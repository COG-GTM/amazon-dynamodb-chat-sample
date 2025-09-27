# -*- coding: utf-8 -*-
import json
from http import HTTPStatus
from pymongo import MongoClient


def test_get_all_comments(client):
    response = client.get('/chat/comments/all')

    print('test_get_all_comments:' + str(response.json.items()))
    assert response.status_code == HTTPStatus.OK
    assert 'response' in response.json


def test_get_latest_comment(client):
    response = client.get('/chat/comments/latest')

    print('test_get_latest_comment ;' + str(response.json.items()))
    assert response.status_code == HTTPStatus.OK
    assert 'response' in response.json


def test_get_range_comment(client):
    latest_seq_id = '1111'
    uri = ('/chat/comments/latest/' + latest_seq_id)
    response = client.get(uri)

    print('test_get_range_comment ;' + str(response.json.items()))
    assert response.status_code == HTTPStatus.OK
    assert 'response' in response.json


def test_put_add_comment(client):
    response = client.post('/chat/comments/add',
                           headers={'Content-Type': 'application/json'},
                           body=json.dumps({'name': 'oranie', 'comment': 'test done'}))

    client_mongo = MongoClient('mongodb://localhost:27017/')
    db = client_mongo.chat_app_test
    collection = db.chat

    get_result = collection.find_one({
        'name': 'oranie',
        'time': str(response.json['time'])
    })

    print('Get Item : ' + str(get_result))

    assert response.status_code == HTTPStatus.OK
    assert response.json['state'] == 'Commment add OK'
    assert 'time' in response.json
    assert get_result is not None
    assert 'oranie' in get_result['name']
    assert 'test done' in get_result['comment']


def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    from chalicelib.mongodb import test_mongodb_connection
    assert test_mongodb_connection() is True


def test_mongodb_indexing():
    """Test that MongoDB indexes are properly created"""
    client = MongoClient('mongodb://localhost:27017/')
    db = client.chat_app_test
    collection = db.chat

    indexes = list(collection.list_indexes())
    index_names = [idx['name'] for idx in indexes]

    assert len(indexes) >= 3
    assert any('name_1_time_1' in name for name in index_names)
    assert any('chat_room_1_time_-1' in name for name in index_names)


def test_empty_chat_room(client):
    """Test API behavior with empty chat room"""
    response = client.get('/chat/comments/all')
    assert response.status_code == HTTPStatus.OK
    assert 'response' in response.json
