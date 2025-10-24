import pymongo
import sys

try:
    client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✓ Successfully connected to MongoDB")
    
    db = client['chat']
    collection = db['chat']
    
    result = collection.find_one()
    print(f"✓ Successfully accessed chat database and collection")
    print(f"✓ Found document: {result}")
    
    client.close()
    print("\n✓ All MongoDB connectivity tests passed!")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ MongoDB connection failed: {e}")
    sys.exit(1)
