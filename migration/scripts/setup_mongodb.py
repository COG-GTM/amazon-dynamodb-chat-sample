#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB Environment Setup Script

This script sets up the MongoDB environment for the chat application,
including database creation, collection creation, and index setup.

Usage:
    python setup_mongodb.py [options]

Options:
    --mongodb-uri       MongoDB connection URI
    --mongodb-database  MongoDB database name (default: chat_app)
    --mongodb-collection MongoDB collection name (default: messages)
    --drop-existing     Drop existing collection before setup (use with caution!)

Environment Variables:
    MONGODB_URI         MongoDB connection URI (can also use --mongodb-uri)

Example:
    # Local MongoDB
    python setup_mongodb.py --mongodb-uri mongodb://localhost:27017

    # MongoDB Atlas
    python setup_mongodb.py --mongodb-uri "mongodb+srv://user:pass@cluster.mongodb.net"

    # With environment variable
    export MONGODB_URI="mongodb://localhost:27017"
    python setup_mongodb.py
"""

import argparse
import logging
import os
import sys
from typing import Dict, List

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, CollectionInvalid
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


class MongoDBSetup:
    """Handles MongoDB environment setup."""

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

    def get_server_info(self) -> Dict:
        """Get MongoDB server information."""
        return self.client.server_info()

    def create_database_and_collection(self, drop_existing: bool = False) -> None:
        """
        Create the database and collection.

        Args:
            drop_existing: If True, drop existing collection first
        """
        logger.info(f"Setting up database: {self.database_name}")
        logger.info(f"Setting up collection: {self.collection_name}")

        if drop_existing:
            if self.collection_name in self.db.list_collection_names():
                logger.warning(f"Dropping existing collection: {self.collection_name}")
                self.db.drop_collection(self.collection_name)

        # Create collection if it doesn't exist
        if self.collection_name not in self.db.list_collection_names():
            try:
                self.db.create_collection(self.collection_name)
                logger.info(f"Created collection: {self.collection_name}")
            except CollectionInvalid:
                logger.info(f"Collection already exists: {self.collection_name}")
        else:
            logger.info(f"Collection already exists: {self.collection_name}")

    def create_indexes(self) -> List[str]:
        """
        Create required indexes on the collection.

        Returns:
            List of created index names
        """
        logger.info("Creating indexes...")
        created_indexes = []

        # Index 1: chat_room + time (replaces DynamoDB GSI)
        # This index supports:
        # - getLatestComments: filter by chat_room, sort by time desc
        # - getRangeComments: filter by chat_room and time > position
        # - getAllComments: filter by chat_room, sort by time desc
        index_name = "chat_room_time_idx"
        try:
            self.collection.create_index(
                [("chat_room", ASCENDING), ("time", DESCENDING)],
                name=index_name,
                background=True
            )
            logger.info(f"  Created index: {index_name}")
            created_indexes.append(index_name)
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"  Index already exists: {index_name}")
            else:
                logger.error(f"  Error creating index {index_name}: {e}")

        # Index 2: name + time (unique constraint, replaces DynamoDB primary key)
        # This ensures no duplicate messages from same user at same timestamp
        index_name = "name_time_unique_idx"
        try:
            self.collection.create_index(
                [("name", ASCENDING), ("time", ASCENDING)],
                name=index_name,
                unique=True,
                background=True
            )
            logger.info(f"  Created index: {index_name}")
            created_indexes.append(index_name)
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"  Index already exists: {index_name}")
            else:
                logger.error(f"  Error creating index {index_name}: {e}")

        return created_indexes

    def verify_setup(self) -> Dict:
        """
        Verify the MongoDB setup.

        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying setup...")

        results = {
            'database_exists': self.database_name in self.client.list_database_names(),
            'collection_exists': self.collection_name in self.db.list_collection_names(),
            'indexes': [],
            'document_count': 0
        }

        # Get index information
        for index in self.collection.list_indexes():
            results['indexes'].append({
                'name': index.get('name'),
                'keys': dict(index.get('key', {})),
                'unique': index.get('unique', False)
            })

        # Get document count
        results['document_count'] = self.collection.count_documents({})

        return results

    def insert_sample_data(self) -> None:
        """Insert sample data for testing."""
        logger.info("Inserting sample data...")

        sample_documents = [
            {
                'name': 'Alice',
                'time': '1000000.000000',
                'comment': 'Hello, this is a test message!',
                'chat_room': 'chat'
            },
            {
                'name': 'Bob',
                'time': '1000001.000000',
                'comment': 'Hi Alice, welcome to the chat!',
                'chat_room': 'chat'
            },
            {
                'name': 'Charlie',
                'time': '1000002.000000',
                'comment': 'Good to see everyone here.',
                'chat_room': 'chat'
            }
        ]

        try:
            result = self.collection.insert_many(sample_documents, ordered=False)
            logger.info(f"  Inserted {len(result.inserted_ids)} sample documents")
        except Exception as e:
            if "duplicate key" in str(e).lower():
                logger.info("  Sample data already exists (skipping duplicates)")
            else:
                logger.error(f"  Error inserting sample data: {e}")

    def close(self) -> None:
        """Close MongoDB connection."""
        self.client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Set up MongoDB environment for chat application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
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
        '--drop-existing',
        action='store_true',
        help='Drop existing collection before setup (use with caution!)'
    )
    parser.add_argument(
        '--with-sample-data',
        action='store_true',
        help='Insert sample data after setup'
    )

    args = parser.parse_args()

    try:
        # Initialize setup
        setup = MongoDBSetup(
            uri=args.mongodb_uri,
            database=args.mongodb_database,
            collection=args.mongodb_collection
        )

        # Print server info
        server_info = setup.get_server_info()
        logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")

        logger.info("=" * 50)
        logger.info("MongoDB Environment Setup")
        logger.info("=" * 50)

        # Create database and collection
        setup.create_database_and_collection(drop_existing=args.drop_existing)

        # Create indexes
        setup.create_indexes()

        # Insert sample data if requested
        if args.with_sample_data:
            setup.insert_sample_data()

        # Verify setup
        logger.info("=" * 50)
        logger.info("Verification Results")
        logger.info("=" * 50)

        results = setup.verify_setup()
        logger.info(f"Database exists: {results['database_exists']}")
        logger.info(f"Collection exists: {results['collection_exists']}")
        logger.info(f"Document count: {results['document_count']}")
        logger.info("Indexes:")
        for idx in results['indexes']:
            unique_str = " (unique)" if idx['unique'] else ""
            logger.info(f"  - {idx['name']}: {idx['keys']}{unique_str}")

        logger.info("=" * 50)
        logger.info("Setup Complete!")
        logger.info("=" * 50)

        # Cleanup
        setup.close()
        sys.exit(0)

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
