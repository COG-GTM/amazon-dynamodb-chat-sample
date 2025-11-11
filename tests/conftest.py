# -*- coding: utf-8 -*-
import os

from pymongo import MongoClient, ASCENDING, DESCENDING
import pytest

from app import app as chalice_app

COLLECTION_NAME = 'chat'

if os.environ['API_ENDPOINT'] == 'localhost':
    client = MongoClient('mongodb://localhost:27017')
else:
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    client = MongoClient(mongodb_uri)

db = client['chat_db']
collection = db[COLLECTION_NAME]


@pytest.fixture
def app():
    return chalice_app


def _create_test_mongodb_collection():
    collection.create_index([('chat_room', ASCENDING), ('time', DESCENDING)], name='chat_room_time_idx')
    collection.create_index([('name', ASCENDING), ('time', ASCENDING)], unique=True, name='name_time_idx')
    return collection


def mongodb_test_data_put():
    collection.insert_one({
        'name': 'test_name',
        'time': 'test_time',
        'comment': 'test_data',
        'chat_room': 'test_chat'
    })


@pytest.fixture(autouse=True, scope='session')
def ddb_table():
    _create_test_mongodb_collection()
    mongodb_test_data_put()

    yield collection
    collection.drop()
