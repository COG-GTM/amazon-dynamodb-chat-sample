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

    mongo_client = MongoClient('mongodb://localhost:27017')
    db = mongo_client['chat_db']
    collection = db['chat']
    get_result = collection.find_one({
        'name': 'oranie',
        'time': str(response.json['time'])
    })

    print('Get Item : ' + str(get_result))

    assert response.status_code == HTTPStatus.OK
    assert response.json['state'] == 'Commment add OK'
    assert 'time' in response.json
    assert 'oranie' in get_result['name']
    assert 'test done' in get_result['comment']
