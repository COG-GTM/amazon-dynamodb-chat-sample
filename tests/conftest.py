# -*- coding: utf-8 -*-
import os

import boto3
import pytest

from app import app as chalice_app

DDB_TABLE_NAME = 'chat'  # TODO: Better to acquire from other constant or configured env var

if os.environ['API_ENDPOINT'] == 'localhost':
    ddb = boto3.resource('dynamodb',
                        endpoint_url='http://localhost:8000',
                        region_name=os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-1'))
else:
    ddb = boto3.resource('dynamodb')

table = ddb.Table(DDB_TABLE_NAME)

MONGO_COLLECTION_NAME = 'chat'

try:
    import pymongo

    mongo_client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
    mongo_db = mongo_client.chat_db_test
    mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
    mongo_client.server_info()
    MONGODB_AVAILABLE = True
except (ImportError, pymongo.errors.ServerSelectionTimeoutError, pymongo.errors.ConnectionFailure):
    MONGODB_AVAILABLE = False
    mongo_collection = None


def _create_test_mongo_collection():
    if MONGODB_AVAILABLE:
        mongo_collection.create_index([('name', 1), ('time', 1)], unique=True)
        mongo_collection.create_index([('chat_room', 1), ('time', -1)])
    return mongo_collection


def mongo_test_data_put():
    if MONGODB_AVAILABLE:
        mongo_collection.insert_one({
            'name': 'test_name',
            'time': 'test_time',
            'comment': 'test_data',
            'chat_room': 'test_chat'
        })


@pytest.fixture(autouse=True, scope='session')
def mongo_collection_fixture():
    if MONGODB_AVAILABLE:
        _create_test_mongo_collection()
        mongo_test_data_put()
        yield mongo_collection
        mongo_collection.drop()
    else:
        yield None


@pytest.fixture
def app():
    return chalice_app


def _create_test_ddb_table():
    return ddb.create_table(
        TableName=DDB_TABLE_NAME,
        AttributeDefinitions=[
            {
                'AttributeName': 'name',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'time',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'chat_room',
                'AttributeType': 'S',
            },
        ],
        KeySchema=[
            {
                'AttributeName': 'name',
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'time',
                'KeyType': 'RANGE',
            },
        ],
        GlobalSecondaryIndexes=[{
            'IndexName': 'chat_room_time_idx',
            'KeySchema': [
                {
                    'AttributeName': 'chat_room',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'time',
                    'KeyType': 'RANGE',
                },
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 100,
                'WriteCapacityUnits': 100
            }
        }],
        ProvisionedThroughput={
            'ReadCapacityUnits': 100,
            'WriteCapacityUnits': 100
        },

    )


def ddb_test_data_put():
    table.put_item(
        Item={
            'name': 'test_name',
            'time': 'test_time',
            'comment': 'test_data',
            'chat_room': 'test_chat'
        },
        ReturnValues='ALL_OLD',
        ReturnConsumedCapacity='TOTAL'
    )


@pytest.fixture(autouse=True, scope='session')
def ddb_table():
    _create_test_ddb_table()
    table.wait_until_exists()
    ddb_test_data_put()

    yield table
    table.delete()
    table.wait_until_not_exists()
