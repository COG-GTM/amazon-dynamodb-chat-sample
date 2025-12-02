# MongoDB Migration - Phase 1: Data Model Design

This directory contains the deliverables for Phase 1 of the DynamoDB to MongoDB migration.

## Contents

- `SCHEMA_DESIGN.md` - Comprehensive schema design document with design decisions
- `requirements.txt` - Python dependencies for migration scripts
- `scripts/` - Migration and setup scripts
  - `create_indexes.js` - MongoDB shell script for index creation
  - `migrate_dynamodb_to_mongodb.py` - Data migration script
  - `setup_mongodb.py` - MongoDB environment setup script

## Quick Start

### 1. Install Dependencies

```bash
cd migration
pip install -r requirements.txt
```

### 2. Set Up MongoDB Environment

For local MongoDB:
```bash
python scripts/setup_mongodb.py --mongodb-uri mongodb://localhost:27017
```

For MongoDB Atlas:
```bash
python scripts/setup_mongodb.py --mongodb-uri "mongodb+srv://user:password@cluster.mongodb.net"
```

With sample data:
```bash
python scripts/setup_mongodb.py --mongodb-uri mongodb://localhost:27017 --with-sample-data
```

### 3. Run Data Migration

From local DynamoDB:
```bash
python scripts/migrate_dynamodb_to_mongodb.py \
    --dynamodb-endpoint http://localhost:8000 \
    --mongodb-uri mongodb://localhost:27017
```

From AWS DynamoDB:
```bash
python scripts/migrate_dynamodb_to_mongodb.py \
    --mongodb-uri "mongodb+srv://user:password@cluster.mongodb.net"
```

Dry run (preview without writing):
```bash
python scripts/migrate_dynamodb_to_mongodb.py \
    --dynamodb-endpoint http://localhost:8000 \
    --mongodb-uri mongodb://localhost:27017 \
    --dry-run
```

### 4. Create Indexes (Alternative Method)

Using MongoDB shell:
```bash
mongosh mongodb://localhost:27017 scripts/create_indexes.js
```

## MongoDB Schema

### Collection: `messages`

```json
{
  "_id": ObjectId("..."),
  "name": "Alice",
  "time": "1572940800.123456",
  "comment": "Hello, world!",
  "chat_room": "chat"
}
```

### Indexes

1. **chat_room_time_idx**: `{ chat_room: 1, time: -1 }`
   - Replaces DynamoDB GSI for efficient chat room queries

2. **name_time_unique_idx**: `{ name: 1, time: 1 }` (unique)
   - Enforces uniqueness constraint matching DynamoDB primary key

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `AWS_REGION` | AWS region for DynamoDB | `us-east-1` |

## Next Steps

After completing Phase 1, proceed to:
- **Phase 2**: Implement MongoDB data access layer (`chalicelib/mongodb.py`)
- **Phase 3**: Update API layer to use MongoDB
- **Phase 4**: Configuration and deployment updates
