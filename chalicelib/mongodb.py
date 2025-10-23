# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

import pymongo
from pymongo.errors import DuplicateKeyError

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def create_connection(collection_name):
    client = None
    if os.getenv('API_ENDPOINT') != 'localhost':
        connection_string = os.getenv('MONGODB_CONNECTION_STRING')
        if not connection_string:
            raise ValueError('MONGODB_CONNECTION_STRING environment variable not set')
        client = pymongo.MongoClient(connection_string)
    else:
        client = pymongo.MongoClient('mongodb://localhost:27017')

    db_name = os.getenv('MONGODB_DATABASE', 'chat_db')
    db = client[db_name]
    collection = db[collection_name]

    collection.create_index([('name', pymongo.ASCENDING), ('time', pymongo.ASCENDING)], unique=True)
    collection.create_index([('chat_room', pymongo.ASCENDING), ('time', pymongo.DESCENDING)])

    return collection


class MongoChat():
    def putComment(self, collection, name, comment, chat_room):
        logging.info('PutComments params : %s %s %s %s', collection.name, name, comment, chat_room)
        now = str(datetime.now().timestamp())

        try:
            collection.insert_one({
                'name': name,
                'time': now,
                'comment': comment,
                'chat_room': chat_room
            })

            response = {
                'Attributes': {},
                'ConsumedCapacity': {
                    'CapacityUnits': 1.0,
                    'TableName': collection.name
                },
                'time': now
            }

            logging.info('insert_one result: %s', response)
            return response

        except DuplicateKeyError:
            raise Exception('ConditionalCheckFailedException: Item with same name and time already exists')

    def getLatestComments(self, collection, chat_room, item_count):
        logging.info('getLatestComments params : %s %s', collection.name, chat_room)

        cursor = collection.find(
            {'chat_room': chat_room}
        ).sort('time', pymongo.DESCENDING).limit(item_count)

        items = list(cursor)

        for item in items:
            if '_id' in item:
                item['_id'] = str(item['_id'])

        response = {
            'Items': items,
            'Count': len(items),
            'ScannedCount': len(items)
        }

        return response

    def getRangeComments(self, collection, chat_room, position):
        logging.info('getRangeComments params : %s %s %s', collection.name, chat_room, str(position))

        result = []

        cursor = collection.find(
            {
                'chat_room': chat_room,
                'time': {'$gt': position}
            }
        ).sort('time', pymongo.DESCENDING)

        for item in cursor:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            result.append(item)

        return result

    def getAllComments(self, collection, chat_room):
        logging.info('getAllComments params : %s %s', collection.name, chat_room)

        result = []

        cursor = collection.find(
            {'chat_room': chat_room}
        ).sort('time', pymongo.DESCENDING)

        for item in cursor:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            result.append(item)

        return result
