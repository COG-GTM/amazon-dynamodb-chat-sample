# -*- coding: utf-8 -*-
import os
import pytest
from pymongo import MongoClient
from app import app as chalice_app

COLLECTION_NAME = 'chat'
DB_NAME = 'chat_app'


def get_test_mongodb_client():
    if os.environ.get('API_ENDPOINT') == 'localhost':
        return MongoClient('mongodb://localhost:27017/')
    else:
        return MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/'))


@pytest.fixture
def app():
    return chalice_app


def _create_test_mongodb_collection():
    client = get_test_mongodb_client()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    collection.create_index([("name", 1), ("time", 1)])
    collection.create_index([("chat_room", 1), ("time", -1)])

    return collection


def mongodb_test_data_put(collection):
    collection.insert_one({
        'name': 'test_name',
        'time': 'test_time',
        'comment': 'test_data',
        'chat_room': 'test_chat'
    })


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv('API_ENDPOINT', 'localhost')
    monkeypatch.setenv('MONGODB_URI', f'mongodb://localhost:27017/{DB_NAME}')


@pytest.fixture(autouse=True, scope='session')
def mongodb_collection():
    collection = _create_test_mongodb_collection()
    mongodb_test_data_put(collection)

    yield collection

    client = get_test_mongodb_client()
    client.drop_database(DB_NAME)
