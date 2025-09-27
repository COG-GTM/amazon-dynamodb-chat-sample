# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

from pymongo import MongoClient, DESCENDING

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def create_connection(collection_name):
    if os.getenv('API_ENDPOINT') != 'localhost':
        client = MongoClient(os.getenv('MONGODB_URI'))
    else:
        client = MongoClient('mongodb://localhost:27017/')

    db = client.chat_app
    return db[collection_name]


def setup_mongodb_schema(db):
    # Create indexes for chat_messages collection
    db.chat_messages.create_index([("name", 1), ("time", 1)])  # Primary compound index
    db.chat_messages.create_index([("chat_room", 1), ("time", -1)])  # Chat room index


def test_mongodb_connection():
    try:
        collection = create_connection('chat_messages')
        collection.find_one()
        return True
    except Exception as e:
        logging.error('MongoDB connection test failed: %s', str(e))
        return False


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

            response = {
                'time': now,
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            logging.info('insert_one result :' + str(response))
            return response

        except Exception as e:
            logging.error('Error inserting comment: %s', str(e))
            raise

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
            'Count': len(items)
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
    result = mongo.getLatestComments(collection, chat_room)

    list = result['Items']
    for index, item in enumerate(list):
        logging.info(f"id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    result = mongo.getAllComments(collection, chat_room)
    for index, item in enumerate(result):
        logging.info(
            f"ALL Result id: {str(index)} name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)

    result = mongo.getRangeComments(collection, chat_room, 0)

    for index, item in enumerate(result):
        logging.info(
            f"RANGE Result id: {str(index)}name: {item['name']} time: {str(item['time'])} comment: {item['comment']}")

    logging.info(result)
"""
