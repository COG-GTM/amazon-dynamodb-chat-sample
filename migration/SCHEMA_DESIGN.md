# MongoDB Schema Design Document

## Phase 1: Data Model Design for DynamoDB to MongoDB Migration

### Overview

This document describes the MongoDB schema design to replace the existing DynamoDB single-table design for the chat application. The migration aims to maintain full API compatibility while leveraging MongoDB's document model and indexing capabilities.

### Current DynamoDB Structure

The existing DynamoDB table has the following structure:

**Table Name:** `chat`

**Primary Key (Composite):**
- Partition Key: `name` (String) - User name who posted the message
- Sort Key: `time` (String) - Unix timestamp of the message

**Attributes:**
- `name` (String): User name
- `time` (String): Unix timestamp (e.g., "1572940800.123456")
- `comment` (String): Message content
- `chat_room` (String): Chat room identifier

**Global Secondary Index (GSI):**
- Index Name: `chat_room_time_idx`
- Partition Key: `chat_room` (String)
- Sort Key: `time` (String)
- Projection: ALL attributes

### Query Patterns Analysis

The application uses the following query patterns:

1. **Insert Message** (`putComment`): Insert a new chat message with conditional check to prevent duplicates based on name+time combination.

2. **Get Latest Messages** (`getLatestComments`): Retrieve the N most recent messages from a specific chat room, sorted by time descending. Uses the GSI.

3. **Get Range Messages** (`getRangeComments`): Retrieve all messages from a chat room where time is greater than a specified position. Used for incremental updates. Uses the GSI.

4. **Get All Messages** (`getAllComments`): Retrieve all messages from a specific chat room, sorted by time descending. Uses the GSI with pagination.

### MongoDB Schema Design

#### Collection: `messages`

I chose to use a single `messages` collection rather than multiple collections because the application only has one entity type (chat messages) and all query patterns operate on the same data structure.

**Document Structure:**

```json
{
  "_id": ObjectId("..."),
  "name": "Alice",
  "time": "1572940800.123456",
  "comment": "Hello, world!",
  "chat_room": "chat"
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | MongoDB auto-generated unique identifier |
| `name` | String | User name who posted the message |
| `time` | String | Unix timestamp (kept as string for API compatibility) |
| `comment` | String | Message content |
| `chat_room` | String | Chat room identifier |

#### Design Decisions

**1. Single Collection Approach**

The application deals with a single entity type (chat messages), so using a single collection is the most straightforward approach. There's no benefit to splitting data across multiple collections since all queries operate on the same document structure.

**2. Timestamp as String**

The `time` field is kept as a String type to maintain backward compatibility with the existing API. The current application stores timestamps as string representations of Unix timestamps (e.g., "1572940800.123456"). Converting to MongoDB's Date type would require changes to the API layer.

**Future Improvement:** Consider adding a `created_at` field with proper Date type for new documents while keeping the `time` field for compatibility. This would enable better date-based queries and aggregations.

**3. MongoDB ObjectId vs Custom ID**

I chose to use MongoDB's auto-generated ObjectId for `_id` rather than creating a composite key from `name` + `time`. This approach:
- Simplifies document insertion
- Avoids potential issues with special characters in user names
- Maintains uniqueness through a compound unique index instead

**4. Uniqueness Constraint**

The DynamoDB table uses `name` + `time` as a composite primary key, ensuring uniqueness. In MongoDB, this is achieved through a compound unique index on `{name: 1, time: 1}`.

### Index Strategy

The following indexes replace the DynamoDB GSI functionality and ensure efficient query execution:

#### Index 1: Chat Room + Time (Primary Query Index)

```javascript
db.messages.createIndex(
  { "chat_room": 1, "time": -1 },
  { name: "chat_room_time_idx" }
)
```

**Purpose:** This compound index directly replaces the DynamoDB GSI `chat_room_time_idx`. It supports:
- Filtering by `chat_room` (equality)
- Sorting by `time` (descending)
- Range queries on `time` within a chat room

**Query Patterns Supported:**
- `getLatestComments`: Filter by chat_room, sort by time desc, limit N
- `getRangeComments`: Filter by chat_room and time > position
- `getAllComments`: Filter by chat_room, sort by time desc

#### Index 2: Name + Time (Uniqueness Constraint)

```javascript
db.messages.createIndex(
  { "name": 1, "time": 1 },
  { name: "name_time_unique_idx", unique: true }
)
```

**Purpose:** Enforces the same uniqueness constraint as the DynamoDB primary key. Prevents duplicate messages from the same user at the exact same timestamp.

### Index Creation Script

See `migration/scripts/create_indexes.js` for the complete index creation script.

### Data Migration Strategy

The migration script (`migration/scripts/migrate_dynamodb_to_mongodb.py`) performs the following steps:

1. **Connect to DynamoDB:** Establish connection to the source DynamoDB table
2. **Scan All Items:** Use pagination to retrieve all items from the DynamoDB table
3. **Transform Documents:** Convert DynamoDB item format to MongoDB document format
4. **Insert to MongoDB:** Bulk insert documents into the MongoDB collection
5. **Verify Migration:** Compare document counts and sample data

### API Compatibility

The MongoDB schema maintains full compatibility with the existing API:

| API Endpoint | DynamoDB Operation | MongoDB Operation |
|--------------|-------------------|-------------------|
| POST /chat/comments/add | put_item | insert_one |
| GET /chat/comments/latest | query (GSI, limit) | find().sort().limit() |
| GET /chat/comments/all | query (GSI, paginated) | find().sort() |
| GET /chat/comments/latest/{seq_id} | query (GSI, range) | find({time: {$gt: seq_id}}).sort() |

### Performance Considerations

1. **Index Coverage:** The `chat_room_time_idx` index covers all read query patterns, ensuring efficient query execution without collection scans.

2. **Write Performance:** Single document inserts are efficient. The unique index on `name` + `time` adds minimal overhead.

3. **Pagination:** MongoDB's cursor-based pagination replaces DynamoDB's `LastEvaluatedKey` mechanism.

4. **Scaling:** For high-volume chat applications, consider:
   - Sharding on `chat_room` for horizontal scaling
   - TTL index for automatic message expiration
   - Capped collections for fixed-size chat history

### Future Improvements

1. **Date Type Migration:** Add proper Date field for new messages
2. **Message ID:** Consider adding a sequential message ID per chat room
3. **User References:** If user management is added, consider referencing user documents
4. **Read Receipts:** Schema can be extended with embedded arrays for read receipts
