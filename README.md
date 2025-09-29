## This project is a MongoDB Chat Application (migrated from DynamoDB)


![codebuild](https://codebuild.ap-northeast-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiL1RBME9sdkZScDFhMjc4M1NhTE1JK3VjUVppaXZURzdRb3dwaXRmVktDWkR4Sy9pMEppcGczU2JnNDVldHg1RkZsaHNCTno4Z2UwWmNmNzBKKzRYdjRBPSIsIml2UGFyYW1ldGVyU3BlYyI6InI1UXVGUFBPYzFJMkJTSDQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)



Realtime Comment Demo App

![demo](./demo.gif)


## High level architecture
![architecture](./demo_arch.png)

## Environment
MongoDB (using compound indexes)

Python 3.9+

Please read Chalice project doc.
https://github.com/aws/chalice

Local testing requires MongoDB (either MongoDB Community Edition or using Docker).
https://docs.mongodb.com/manual/installation/

Set MONGODB_URI environment variable to specify your MongoDB connection:
- Local: `mongodb://localhost:27017` 
- Cloud: Your MongoDB Atlas connection string

Example: `export MONGODB_URI=mongodb://localhost:27017`
# MongoDB Setup

## Local Development (MongoDB)

### Option 1: Using Docker (Recommended)
```bash
# Start MongoDB locally using Docker
docker run --name mongodb-chat -p 27017:27017 -d mongo:latest

# Verify MongoDB is running
docker ps | grep mongodb-chat
```

### Option 2: Install MongoDB Locally
Follow the MongoDB Community Edition installation guide for your OS:
https://docs.mongodb.com/manual/installation/

## MongoDB Schema

The application will automatically create the required database and collection on first use.

Indexes are created automatically:
```javascript
db.chat.createIndex({ "name": 1, "time": 1 })

db.chat.createIndex({ "chat_room": 1, "time": -1 })
```

Database: `chat_app`
Collection: `chat`

## Deploy
This operation needs IAM permission for chalice deploy and using MongoDB. Please check chalice document.

https://github.com/aws/chalice#credentials

### Local App Start

1. **Start MongoDB** (if not already running):
   ```bash
   # Using Docker
   docker run --name mongodb-chat -p 27017:27017 -d mongo:latest
   
   # Or start your local MongoDB service
   # macOS: brew services start mongodb-community
   # Linux: sudo systemctl start mongod
   ```

2. **Set environment variable**:
   ```bash
   export MONGODB_URI=mongodb://localhost:27017
   ```

3. **Start the Chalice application**:
   ```bash
   chalice local --stage local --port 8080
   ```

4. **Access the application**:
   Open http://localhost:8080/chat in your browser

# Production Deployment

## Prerequisites

1. **Set up MongoDB Atlas** (or your preferred MongoDB hosting):
   - Create a free account at https://www.mongodb.com/cloud/atlas
   - Create a new cluster
   - Set up database access (username/password)
   - Whitelist your IP addresses or use 0.0.0.0/0 for testing
   - Get your connection string from the "Connect" button

2. **Configure AWS credentials for Chalice**:
   https://github.com/aws/chalice#credentials

## Deployment Steps

### Step 1: Deploy the Lambda function
```bash
chalice deploy
```

This will output your API Gateway endpoint URL, for example:
```
Resources deployed:
  - Lambda ARN: arn:aws:lambda:ap-northeast-1:YOUR_ACCOUNT_ID:function:dynamodb-python-chat-sample-dev
  - Rest API URL: https://xxxxx.execute-api.region.amazonaws.com/api/
```

### Step 2: Update .chalice/config.json with your MongoDB connection string

Edit `.chalice/config.json`:
```json
{
  "version": "2.0",
  "app_name": "dynamodb-python-chat-sample",
  "autogen_policy": false,
  "lambda_memory_size": 2048,
  "stages": {
    "dev": {
      "environment_variables": {
        "MONGODB_URI": "mongodb+srv://username:password@cluster.mongodb.net/chat_app?retryWrites=true&w=majority"
      }
    }
  }
}
```

**Important**: Replace the MONGODB_URI value with your actual MongoDB Atlas connection string.

### Step 3: Re-deploy with MongoDB configuration
```bash
chalice deploy
```

### Alternative: Self-Hosted MongoDB

If using a self-hosted MongoDB instance:
1. Ensure your MongoDB server is accessible from AWS Lambda
2. Configure network security groups and VPC settings
3. Use the appropriate connection string format:
   - Standard: `mongodb://host:port/database`
   - With authentication: `mongodb://username:password@host:port/database`

### Alternative: Using AWS Secrets Manager

For production, store your MongoDB connection string in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
    --name mongodb-connection-string \
    --secret-string "mongodb+srv://username:password@cluster.mongodb.net/chat_app"
```

Then update your Lambda function to retrieve the secret at runtime.

## Python Test

pytest should be run without a chat table. If there is an existing table, the test will fail. 

Project root dir "pytest -vv" 



## MongoDB Data Model

### Collection: chat
**Database**: `chat_app`

**Document Schema**:
| Field | Type | Description |
|-------|------|-------------|
| name | string | Username of the commenter |
| time | string | Timestamp (Unix timestamp with microseconds) |
| comment | string | The chat message content |
| chat_room | string | Chat room identifier |
| _id | ObjectId | MongoDB document ID (auto-generated) |

### Indexes

**Compound Index 1** (replaces DynamoDB primary key):
| Field | Order | Purpose |
|-------|-------|---------|
| name | 1 (ascending) | User-based queries |
| time | 1 (ascending) | Time-ordered results |

**Compound Index 2** (replaces DynamoDB GSI):
| Field | Order | Purpose |
|-------|-------|---------|
| chat_room | 1 (ascending) | Chat room filtering |
| time | -1 (descending) | Latest messages first |

This index structure enables efficient queries for:
- All messages from a specific user, ordered by time
- All messages in a chat room, with latest first
- Range queries for incremental message loading


## Legacy DynamoDB Reference

The following images show the original DynamoDB implementation for reference:

![table](./table.png)

![table_sample](./table_sample.png)

![GSI_sample](./GSI_sample.png)

Note: The application has been migrated to MongoDB. These images are kept for historical reference only.

## Data Migration from DynamoDB

If you have existing data in DynamoDB that needs to be migrated to MongoDB, use the provided migration script.

### Migration Script Usage

The `migrate_dynamodb_to_mongodb.py` script supports various migration scenarios:

#### Prerequisites
```bash
pip install boto3 pymongo
```

#### Migration Examples

**1. Local to Local (for testing)**:
```bash
# Ensure both DynamoDB Local and MongoDB are running
python migrate_dynamodb_to_mongodb.py --source local --target local
```

**2. AWS DynamoDB to MongoDB Atlas**:
```bash
# Set up AWS credentials
export AWS_PROFILE=your-aws-profile

# Set MongoDB connection string
export MONGODB_URI="mongodb+srv://username:password@cluster.mongodb.net/chat_app"

# Run migration
python migrate_dynamodb_to_mongodb.py --source aws --target cloud
```

**3. Dry Run (test without migrating)**:
```bash
python migrate_dynamodb_to_mongodb.py --source local --target local --dry-run
```

#### What the Script Does

1. Connects to source DynamoDB (local or AWS)
2. Connects to target MongoDB (local or cloud)
3. Creates required indexes in MongoDB
4. Scans all items from the DynamoDB `chat` table
5. Transforms items to MongoDB document format
6. Checks for duplicates (based on name + time)
7. Inserts new items into MongoDB `chat` collection
8. Provides detailed logging of the migration process

#### Important Notes

- The script will NOT overwrite existing data in MongoDB
- Duplicates are detected and skipped based on `name` and `time` fields
- Use `--dry-run` flag to test the migration without making changes
- For large datasets, the migration may take several minutes
- Ensure network connectivity between your environment and MongoDB/DynamoDB

## API

* /chat

return chat client HTML and js.
    
* /chat/comments/add

client sent post request with name,comment txt, get response add comment status

POST value {"name": "oranie", "comment":"hello world"}


* /chat/comments/all

client sent get request, get all comment.
    
* /chat/comments/latest

client sent get request latest 20 comments.

* /chat/comments/latest/{latest_seq_id}

client sent get request with latest chat id, get the difference comments.
    

# License
This library is licensed under the MIT-0 License. See the LICENSE file.
