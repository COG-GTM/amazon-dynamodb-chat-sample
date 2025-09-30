# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

import pymongo
from pymongo import DESCENDING

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def create_connection(collection_name):
    if os.getenv('API_ENDPOINT') != 'localhost':
        client = pymongo.MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
    else:
        client = pymongo.MongoClient('mongodb://localhost:27017')

    db = client[os.getenv('MONGODB_DATABASE', 'chat_db')]
    collection = db[collection_name]

    collection.create_index([('name', 1), ('time', 1)], unique=True)
    collection.create_index([('chat_room', 1), ('time', -1)])

    return collection


class MongoChat():
    def putComment(self, collection, name, comment, chat_room):
        logging.info('PutComments params : %s %s %s %s', collection, name, comment, chat_room)
        now = str(datetime.now().timestamp())

        try:
            collection.insert_one({
                'name': name,
                'time': now,
                'comment': comment,
                'chat_room': chat_room
            })

            result = {
                'time': now,
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            logging.info('insert_one result :' + str(result))
            return result

        except pymongo.errors.DuplicateKeyError:
            raise Exception('Item with this name and time already exists')

    def getLatestComments(self, collection, chat_room, item_count):
        logging.info('getLatestComments params : %s %s', collection, chat_room)

        cursor = collection.find(
            {'chat_room': chat_room}
        ).sort('time', DESCENDING).limit(item_count)

        items = list(cursor)

        for item in items:
            item.pop('_id', None)

        response = {
            'Items': items,
            'Count': len(items),
            'ScannedCount': len(items)
        }

        return response

    def getRangeComments(self, collection, chat_room, position):
        logging.info('getRangeComments params : %s %s %s', collection, chat_room, str(position))

        cursor = collection.find({
            'chat_room': chat_room,
            'time': {'$gt': position}
        }).sort('time', DESCENDING)

        result = list(cursor)

        for item in result:
            item.pop('_id', None)

        return result

    def getAllComments(self, collection, chat_room):
        logging.info('getAllComments params : %s %s', collection, chat_room)

        cursor = collection.find(
            {'chat_room': chat_room}
        ).sort('time', DESCENDING)

        result = list(cursor)

        for item in result:
            item.pop('_id', None)

        return result


"""
if __name__ == "__main__":
    mongo = MongoChat()
    collection = create_connection('chat')

    name = 'oranie'
    comment = 'チャットシステムです'
    chat_room = 'chat'

    mongo.putComment(collection, name, comment, chat_room)
    result = mongo.getLatestComments(collection, chat_room, 20)

    list = result['Items']
    for index, item in enumerate(list):
        logging.info(f"id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    result = mongo.getAllComments(collection, chat_room)
    for index, item in enumerate(result):
        logging.info(
            f"ALL Result id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)

    result = mongo.getRangeComments(collection, chat_room, '0')

    for index, item in enumerate(result):
        logging.info(
            f"RANGE Result id: {str(index)}name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)
"""
