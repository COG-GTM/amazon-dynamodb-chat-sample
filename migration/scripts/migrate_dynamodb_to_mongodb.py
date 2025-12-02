#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DynamoDB to MongoDB Migration Script

This script migrates chat data from DynamoDB to MongoDB.
It handles pagination for large datasets and performs bulk inserts for efficiency.

Usage:
    python migrate_dynamodb_to_mongodb.py [options]

Options:
    --dynamodb-table    DynamoDB table name (default: chat)
    --dynamodb-endpoint DynamoDB endpoint URL (for local testing)
    --mongodb-uri       MongoDB connection URI
    --mongodb-database  MongoDB database name (default: chat_app)
    --mongodb-collection MongoDB collection name (default: messages)
    --batch-size        Number of documents per batch insert (default: 100)
    --dry-run           Preview migration without writing to MongoDB

Environment Variables:
    AWS_REGION          AWS region for DynamoDB (default: us-east-1)
    MONGODB_URI         MongoDB connection URI (can also use --mongodb-uri)

Example:
    # Local development
    python migrate_dynamodb_to_mongodb.py \\
        --dynamodb-endpoint http://localhost:8000 \\
        --mongodb-uri mongodb://localhost:27017

    # Production
    python migrate_dynamodb_to_mongodb.py \\
        --mongodb-uri "mongodb+srv://user:pass@cluster.mongodb.net"
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import boto3
from botocore.exceptions import ClientError

try:
    from pymongo import MongoClient
    from pymongo.errors import BulkWriteError, ConnectionFailure
except ImportError:
    print("Error: pymongo is required. Install with: pip install pymongo")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DynamoDBSource:
    """Handles reading data from DynamoDB."""

    def __init__(self, table_name: str, endpoint_url: Optional[str] = None,
                 region: str = 'us-east-1'):
        """
        Initialize DynamoDB connection.

        Args:
            table_name: Name of the DynamoDB table
            endpoint_url: Optional endpoint URL for local DynamoDB
            region: AWS region
        """
        self.table_name = table_name

        if endpoint_url:
            logger.info(f"Connecting to DynamoDB at {endpoint_url}")
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=endpoint_url,
                region_name=region
            )
        else:
            logger.info(f"Connecting to DynamoDB in region {region}")
            self.dynamodb = boto3.resource('dynamodb', region_name=region)

        self.table = self.dynamodb.Table(table_name)

    def get_item_count(self) -> int:
        """Get approximate item count from table."""
        try:
            response = self.table.scan(Select='COUNT')
            count = response.get('Count', 0)

            # Handle pagination for count
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    Select='COUNT',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                count += response.get('Count', 0)

            return count
        except ClientError as e:
            logger.error(f"Error getting item count: {e}")
            return 0

    def scan_items(self, batch_size: int = 100) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Scan all items from DynamoDB table with pagination.

        Args:
            batch_size: Number of items to fetch per request

        Yields:
            List of items (dictionaries)
        """
        logger.info(f"Starting scan of table: {self.table_name}")

        try:
            response = self.table.scan(Limit=batch_size)
            items = response.get('Items', [])

            if items:
                yield items

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                logger.debug("Fetching next page from DynamoDB...")
                response = self.table.scan(
                    Limit=batch_size,
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items = response.get('Items', [])
                if items:
                    yield items

        except ClientError as e:
            logger.error(f"Error scanning DynamoDB: {e}")
            raise


class MongoDBTarget:
    """Handles writing data to MongoDB."""

    def __init__(self, uri: str, database: str, collection: str):
        """
        Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI
            database: Database name
            collection: Collection name
        """
        self.uri = uri
        self.database_name = database
        self.collection_name = collection

        logger.info("Connecting to MongoDB...")
        self.client = MongoClient(uri)
        self.db = self.client[database]
        self.collection = self.db[collection]

        # Test connection
        try:
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def create_indexes(self) -> None:
        """Create required indexes on the collection."""
        logger.info("Creating indexes...")

        # Index 1: chat_room + time (replaces DynamoDB GSI)
        self.collection.create_index(
            [("chat_room", 1), ("time", -1)],
            name="chat_room_time_idx",
            background=True
        )
        logger.info("  - Created index: chat_room_time_idx")

        # Index 2: name + time (unique constraint)
        self.collection.create_index(
            [("name", 1), ("time", 1)],
            name="name_time_unique_idx",
            unique=True,
            background=True
        )
        logger.info("  - Created index: name_time_unique_idx")

    def insert_batch(self, documents: List[Dict[str, Any]]) -> int:
        """
        Insert a batch of documents into MongoDB.

        Args:
            documents: List of documents to insert

        Returns:
            Number of documents successfully inserted
        """
        if not documents:
            return 0

        try:
            result = self.collection.insert_many(documents, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as e:
            # Some documents may have been inserted despite errors
            inserted = e.details.get('nInserted', 0)
            write_errors = e.details.get('writeErrors', [])

            # Log duplicate key errors (expected for re-runs)
            duplicates = sum(1 for err in write_errors if err.get('code') == 11000)
            other_errors = len(write_errors) - duplicates

            if duplicates > 0:
                logger.warning(f"  Skipped {duplicates} duplicate documents")
            if other_errors > 0:
                logger.error(f"  {other_errors} documents failed to insert")
                for err in write_errors:
                    if err.get('code') != 11000:
                        logger.error(f"    Error: {err}")

            return inserted

    def get_document_count(self) -> int:
        """Get total document count in collection."""
        return self.collection.count_documents({})

    def close(self) -> None:
        """Close MongoDB connection."""
        self.client.close()


def transform_dynamodb_to_mongodb(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a DynamoDB item to MongoDB document format.

    The DynamoDB item format from boto3 is already deserialized,
    so we just need to ensure the document structure is correct.

    Args:
        item: DynamoDB item (already deserialized by boto3)

    Returns:
        MongoDB document
    """
    # Create MongoDB document with required fields
    document = {
        'name': item.get('name', ''),
        'time': item.get('time', ''),
        'comment': item.get('comment', ''),
        'chat_room': item.get('chat_room', '')
    }

    # Add any additional fields that might exist
    for key, value in item.items():
        if key not in document:
            document[key] = value

    return document


def migrate(
    dynamodb_source: DynamoDBSource,
    mongodb_target: MongoDBTarget,
    batch_size: int = 100,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Perform the migration from DynamoDB to MongoDB.

    Args:
        dynamodb_source: DynamoDB source instance
        mongodb_target: MongoDB target instance
        batch_size: Number of documents per batch
        dry_run: If True, don't write to MongoDB

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        'total_scanned': 0,
        'total_inserted': 0,
        'total_skipped': 0,
        'batches_processed': 0
    }

    logger.info("=" * 50)
    logger.info("Starting migration...")
    logger.info("=" * 50)

    if dry_run:
        logger.info("DRY RUN MODE - No data will be written to MongoDB")

    # Get source count
    source_count = dynamodb_source.get_item_count()
    logger.info(f"Source DynamoDB table has approximately {source_count} items")

    # Create indexes before migration
    if not dry_run:
        mongodb_target.create_indexes()

    start_time = datetime.now()

    # Process batches
    for batch in dynamodb_source.scan_items(batch_size):
        stats['batches_processed'] += 1
        stats['total_scanned'] += len(batch)

        # Transform documents
        documents = [transform_dynamodb_to_mongodb(item) for item in batch]

        if dry_run:
            logger.info(f"  Batch {stats['batches_processed']}: Would insert {len(documents)} documents")
            # Show sample document in dry run
            if stats['batches_processed'] == 1 and documents:
                logger.info(f"  Sample document: {documents[0]}")
        else:
            inserted = mongodb_target.insert_batch(documents)
            stats['total_inserted'] += inserted
            stats['total_skipped'] += len(documents) - inserted

            logger.info(
                f"  Batch {stats['batches_processed']}: "
                f"Inserted {inserted}/{len(documents)} documents "
                f"(Total: {stats['total_inserted']})"
            )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Final statistics
    logger.info("=" * 50)
    logger.info("Migration Complete!")
    logger.info("=" * 50)
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Total scanned from DynamoDB: {stats['total_scanned']}")

    if not dry_run:
        logger.info(f"Total inserted to MongoDB: {stats['total_inserted']}")
        logger.info(f"Total skipped (duplicates): {stats['total_skipped']}")

        # Verify counts
        target_count = mongodb_target.get_document_count()
        logger.info(f"MongoDB collection document count: {target_count}")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate chat data from DynamoDB to MongoDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--dynamodb-table',
        default='chat',
        help='DynamoDB table name (default: chat)'
    )
    parser.add_argument(
        '--dynamodb-endpoint',
        help='DynamoDB endpoint URL (for local testing)'
    )
    parser.add_argument(
        '--mongodb-uri',
        default=os.environ.get('MONGODB_URI', 'mongodb://localhost:27017'),
        help='MongoDB connection URI'
    )
    parser.add_argument(
        '--mongodb-database',
        default='chat_app',
        help='MongoDB database name (default: chat_app)'
    )
    parser.add_argument(
        '--mongodb-collection',
        default='messages',
        help='MongoDB collection name (default: messages)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of documents per batch insert (default: 100)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without writing to MongoDB'
    )
    parser.add_argument(
        '--aws-region',
        default=os.environ.get('AWS_REGION', 'us-east-1'),
        help='AWS region for DynamoDB (default: us-east-1)'
    )

    args = parser.parse_args()

    try:
        # Initialize source
        dynamodb_source = DynamoDBSource(
            table_name=args.dynamodb_table,
            endpoint_url=args.dynamodb_endpoint,
            region=args.aws_region
        )

        # Initialize target
        mongodb_target = MongoDBTarget(
            uri=args.mongodb_uri,
            database=args.mongodb_database,
            collection=args.mongodb_collection
        )

        # Run migration
        stats = migrate(
            dynamodb_source=dynamodb_source,
            mongodb_target=mongodb_target,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )

        # Cleanup
        mongodb_target.close()

        # Exit with appropriate code
        if stats['total_scanned'] == 0:
            logger.warning("No items found in source table")
            sys.exit(0)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
