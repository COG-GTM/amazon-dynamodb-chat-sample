# -*- coding: utf-8 -*-
import json
from http import HTTPStatus

import boto3
import pytest


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

    ddb = boto3.resource('dynamodb', endpoint_url='http://127.0.0.1:8000')
    tbl = ddb.Table('chat')
    get_result = tbl.get_item(
        Key={
            'name': 'oranie',
            'time': str(response.json['time'])
        }
    )

    print('Get Item : ' + str(get_result))

    assert response.status_code == HTTPStatus.OK
    assert response.json['state'] == 'Commment add OK'
    assert 'time' in response.json
    assert 'oranie' in get_result['Item']['name']
    assert 'test done' in get_result['Item']['comment']


def test_mongo_get_all_comments(mongo_collection_fixture):
    if mongo_collection_fixture is None:
        pytest.skip("MongoDB not available")

    from chalicelib.mongodb import MongoChat
    mongo_chat = MongoChat()

    result = mongo_chat.getAllComments(mongo_collection_fixture, 'test_chat')

    assert isinstance(result, list)
    assert len(result) > 0
    assert 'name' in result[0]
    assert 'comment' in result[0]
    assert '_id' not in result[0]


def test_mongo_get_latest_comment(mongo_collection_fixture):
    if mongo_collection_fixture is None:
        pytest.skip("MongoDB not available")

    from chalicelib.mongodb import MongoChat
    mongo_chat = MongoChat()

    result = mongo_chat.getLatestComments(mongo_collection_fixture, 'test_chat', 20)

    assert 'Items' in result
    assert 'Count' in result
    assert isinstance(result['Items'], list)
    if len(result['Items']) > 0:
        assert '_id' not in result['Items'][0]


def test_mongo_get_range_comment(mongo_collection_fixture):
    if mongo_collection_fixture is None:
        pytest.skip("MongoDB not available")

    from chalicelib.mongodb import MongoChat
    mongo_chat = MongoChat()

    result = mongo_chat.getRangeComments(mongo_collection_fixture, 'test_chat', '0')

    assert isinstance(result, list)
    if len(result) > 0:
        assert '_id' not in result[0]


def test_mongo_put_add_comment(mongo_collection_fixture):
    if mongo_collection_fixture is None:
        pytest.skip("MongoDB not available")

    from chalicelib.mongodb import MongoChat
    mongo_chat = MongoChat()

    result = mongo_chat.putComment(
        mongo_collection_fixture,
        'test_user_mongo',
        'test comment from mongo',
        'test_chat'
    )

    assert 'time' in result
    assert 'ResponseMetadata' in result

    inserted = mongo_collection_fixture.find_one({
        'name': 'test_user_mongo',
        'time': result['time']
    })

    assert inserted is not None
    assert inserted['comment'] == 'test comment from mongo'
    assert inserted['chat_room'] == 'test_chat'
