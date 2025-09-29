#!/usr/bin/env python3
"""
Migration script to migrate data from DynamoDB to MongoDB.

This script supports migrating from:
- AWS DynamoDB (cloud)
- DynamoDB Local (for testing)

Usage:
    python migrate_dynamodb_to_mongodb.py --source local --target local

    export AWS_PROFILE=your-profile
    export MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/chat_app
    python migrate_dynamodb_to_mongodb.py --source aws --target cloud

    python migrate_dynamodb_to_mongodb.py --source local --target local --dry-run
"""

import argparse
import logging
import os
import sys
from typing import Dict, List

import boto3
from pymongo import MongoClient
from botocore.exceptions import ClientError

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DynamoDBToMongoDBMigration:
    """Handles migration of chat data from DynamoDB to MongoDB."""

    def __init__(self, source_type: str, target_type: str, dry_run: bool = False):
        self.source_type = source_type
        self.target_type = target_type
        self.dry_run = dry_run
        self.dynamodb_client = None
        self.mongodb_collection = None

    def setup_dynamodb_connection(self):
        """Set up DynamoDB connection based on source type."""
        try:
            if self.source_type == 'local':
                logger.info("Connecting to DynamoDB Local...")
                self.dynamodb_client = boto3.resource(
                    'dynamodb',
                    endpoint_url='http://localhost:8000',
                    region_name='us-west-2',
                    aws_access_key_id='dummy',
                    aws_secret_access_key='dummy'
                )
            else:
                logger.info("Connecting to AWS DynamoDB...")
                self.dynamodb_client = boto3.resource('dynamodb')

            table = self.dynamodb_client.Table('chat')
            table.load()
            logger.info(f"Successfully connected to DynamoDB ({self.source_type})")
            return table

        except ClientError as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to DynamoDB: {e}")
            raise

    def setup_mongodb_connection(self):
        """Set up MongoDB connection based on target type."""
        try:
            if self.target_type == 'local':
                logger.info("Connecting to MongoDB Local...")
                mongodb_uri = 'mongodb://localhost:27017/'
            else:
                mongodb_uri = os.getenv('MONGODB_URI')
                if not mongodb_uri:
                    raise ValueError(
                        "MONGODB_URI environment variable not set for cloud target"
                    )
                logger.info("Connecting to MongoDB Cloud...")

            client = MongoClient(mongodb_uri)
            db = client.chat_app
            self.mongodb_collection = db.chat

            client.server_info()
            logger.info(f"Successfully connected to MongoDB ({self.target_type})")

            logger.info("Creating MongoDB indexes...")
            self.mongodb_collection.create_index([("name", 1), ("time", 1)])
            self.mongodb_collection.create_index([("chat_room", 1), ("time", -1)])
            logger.info("Indexes created successfully")

            return self.mongodb_collection

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def fetch_dynamodb_data(self, table) -> List[Dict]:
        """Fetch all items from DynamoDB table."""
        logger.info("Fetching data from DynamoDB...")
        items = []

        try:
            response = table.scan()
            items.extend(response.get('Items', []))

            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))

            logger.info(f"Fetched {len(items)} items from DynamoDB")
            return items

        except ClientError as e:
            logger.error(f"Error fetching DynamoDB data: {e}")
            raise

    def transform_item(self, item: Dict) -> Dict:
        """Transform DynamoDB item to MongoDB document format."""
        return {
            'name': str(item.get('name', '')),
            'time': str(item.get('time', '')),
            'comment': str(item.get('comment', '')),
            'chat_room': str(item.get('chat_room', ''))
        }

    def migrate_data(self, items: List[Dict]) -> int:
        """Migrate items to MongoDB."""
        if not items:
            logger.warning("No items to migrate")
            return 0

        if self.dry_run:
            logger.info(f"DRY RUN: Would migrate {len(items)} items")
            logger.info(f"Sample item: {items[0] if items else 'N/A'}")
            return len(items)

        logger.info(f"Migrating {len(items)} items to MongoDB...")
        transformed_items = [self.transform_item(item) for item in items]

        try:
            existing_count = 0
            new_items = []

            for item in transformed_items:
                existing = self.mongodb_collection.find_one({
                    'name': item['name'],
                    'time': item['time']
                })
                if existing:
                    existing_count += 1
                else:
                    new_items.append(item)

            if existing_count > 0:
                logger.info(
                    f"Skipping {existing_count} items that already exist in MongoDB"
                )

            if new_items:
                result = self.mongodb_collection.insert_many(new_items)
                logger.info(
                    f"Successfully migrated {len(result.inserted_ids)} new items"
                )
                return len(result.inserted_ids)
            else:
                logger.info("All items already exist in MongoDB")
                return 0

        except Exception as e:
            logger.error(f"Error migrating data to MongoDB: {e}")
            raise

    def run_migration(self):
        """Execute the complete migration process."""
        logger.info("=" * 60)
        logger.info("Starting DynamoDB to MongoDB Migration")
        logger.info(f"Source: DynamoDB ({self.source_type})")
        logger.info(f"Target: MongoDB ({self.target_type})")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info("=" * 60)

        try:
            dynamodb_table = self.setup_dynamodb_connection()
            self.setup_mongodb_connection()

            items = self.fetch_dynamodb_data(dynamodb_table)

            migrated_count = self.migrate_data(items)

            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info(f"Total items processed: {len(items)}")
            logger.info(f"Items migrated: {migrated_count}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Migration failed: {e}")
            logger.error("=" * 60)
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Migrate chat data from DynamoDB to MongoDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--source',
        choices=['local', 'aws'],
        required=True,
        help='Source DynamoDB type (local or aws)'
    )

    parser.add_argument(
        '--target',
        choices=['local', 'cloud'],
        required=True,
        help='Target MongoDB type (local or cloud)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actually migrating data'
    )

    args = parser.parse_args()

    if args.target == 'cloud' and not os.getenv('MONGODB_URI'):
        logger.error(
            "ERROR: MONGODB_URI environment variable must be set for cloud target"
        )
        sys.exit(1)

    migration = DynamoDBToMongoDBMigration(
        source_type=args.source,
        target_type=args.target,
        dry_run=args.dry_run
    )

    success = migration.run_migration()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
