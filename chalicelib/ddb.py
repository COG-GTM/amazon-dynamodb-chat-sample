# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import DuplicateKeyError

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def create_connection(collection_name):
    client = None
    if os.getenv('API_ENDPOINT') != 'localhost':
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        client = MongoClient(mongodb_uri)
    else:
        client = MongoClient('mongodb://localhost:27017')

    db = client['chat_db']
    collection = db[collection_name]

    collection.create_index([('chat_room', ASCENDING), ('time', DESCENDING)], name='chat_room_time_idx')
    collection.create_index([('name', ASCENDING), ('time', ASCENDING)], unique=True, name='name_time_idx')

    return collection


class DdbChat():
    def putComment(self, collection, name, comment, chat_room):
        logging.info('PutComments params : %s %s %s %s', collection, name, comment, chat_room)
        now = str(datetime.now().timestamp())

        document = {
            'name': name,
            'time': now,
            'comment': comment,
            'chat_room': chat_room
        }

        try:
            collection.insert_one(document)
            result = {
                'time': now,
                'ResponseMetadata': {
                    'HTTPStatusCode': 200
                }
            }
            logging.info('insert_one result :' + str(result))
            return result
        except DuplicateKeyError:
            logging.error('Duplicate key error: document with name=%s and time=%s already exists', name, now)
            raise

    def getLatestComments(self, collection, chat_room, item_count):
        logging.info('getLatestComments params : %s %s', collection, chat_room)

        cursor = collection.find({'chat_room': chat_room}).sort('time', DESCENDING).limit(item_count)
        items = []
        for doc in cursor:
            doc.pop('_id', None)
            items.append(doc)

        response = {
            'Items': items,
            'Count': len(items),
            'ScannedCount': len(items)
        }

        return response

    def getRangeComments(self, collection, chat_room, position):
        logging.info('getRangeComments params : %s %s %s', collection, chat_room, str(position))

        result = []

        cursor = collection.find({
            'chat_room': chat_room,
            'time': {'$gt': position}
        }).sort('time', DESCENDING)

        for doc in cursor:
            doc.pop('_id', None)
            result.append(doc)

        return result

    def getAllComments(self, collection, chat_room):
        logging.info('getAllComments params : %s %s', collection, chat_room)

        result = []

        cursor = collection.find({'chat_room': chat_room}).sort('time', DESCENDING)

        for doc in cursor:
            doc.pop('_id', None)
            result.append(doc)

        return result


"""
if __name__ == "__main__":
    ddb = DdbChat()
    table = ddb.createConnection('chat')

    name = 'oranie'
    comment = 'チャットシステムです'
    chat_room = 'chat'

    ddb.putComment(table, name, comment, chat_room)
    result = ddb.getLatestComments(table, chat_room)

    list = result['Items']
    for index, item in enumerate(list):
        logging.info(f"id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    result = ddb.getAllComments(table, chat_room)
    for index, item in enumerate(result):
        logging.info(
            f"ALL Result id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)

    result = ddb.getRangeComments(table, chat_room, 0)

    for index, item in enumerate(result):
        logging.info(
            f"RANGE Result id: {str(index)}name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)
"""
