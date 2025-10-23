# -*- coding: utf-8 -*-
import json
from http import HTTPStatus

import boto3

from chalicelib.mongodb import MongoChat


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


class TestMongoDBIntegration:

    def test_mongo_put_comment(self, mongo_collection):
        mongo_chat = MongoChat()

        result = mongo_chat.putComment(
            mongo_collection,
            'test_user',
            'test comment',
            'test_room'
        )

        assert 'time' in result
        assert result['time'] is not None

        doc = mongo_collection.find_one({'name': 'test_user', 'time': result['time']})
        assert doc is not None
        assert doc['comment'] == 'test comment'
        assert doc['chat_room'] == 'test_room'

    def test_mongo_get_latest_comments(self, mongo_collection):
        mongo_chat = MongoChat()

        for i in range(5):
            mongo_chat.putComment(
                mongo_collection,
                f'user_{i}',
                f'comment_{i}',
                'test_room'
            )

        result = mongo_chat.getLatestComments(mongo_collection, 'test_room', 3)

        assert 'Items' in result
        assert len(result['Items']) <= 3
        assert result['Count'] <= 3

    def test_mongo_get_all_comments(self, mongo_collection):
        mongo_chat = MongoChat()

        result = mongo_chat.getAllComments(mongo_collection, 'test_chat')

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]['chat_room'] == 'test_chat'

    def test_mongo_get_range_comments(self, mongo_collection):
        mongo_chat = MongoChat()

        all_comments = mongo_chat.getAllComments(mongo_collection, 'test_room')

        if len(all_comments) > 0:
            oldest_time = all_comments[-1]['time']

            result = mongo_chat.getRangeComments(mongo_collection, 'test_room', oldest_time)

            assert isinstance(result, list)
            for comment in result:
                assert comment['time'] > oldest_time
