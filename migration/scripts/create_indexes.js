/**
 * MongoDB Index Creation Script
 * 
 * This script creates the necessary indexes for the chat application
 * to replace the DynamoDB GSI functionality.
 * 
 * Usage:
 *   mongosh <connection_string> create_indexes.js
 *   
 * Or in MongoDB shell:
 *   load("create_indexes.js")
 */

// Configuration - Update these values for your environment
const DATABASE_NAME = "chat_app";
const COLLECTION_NAME = "messages";

// Connect to database
const db = db.getSiblingDB(DATABASE_NAME);

print("=== MongoDB Index Creation Script ===");
print(`Database: ${DATABASE_NAME}`);
print(`Collection: ${COLLECTION_NAME}`);
print("");

// Ensure collection exists
if (!db.getCollectionNames().includes(COLLECTION_NAME)) {
    print(`Creating collection: ${COLLECTION_NAME}`);
    db.createCollection(COLLECTION_NAME);
}

const collection = db.getCollection(COLLECTION_NAME);

// Index 1: chat_room + time (replaces DynamoDB GSI)
// This is the primary query index for all read operations
print("Creating index: chat_room_time_idx");
try {
    collection.createIndex(
        { "chat_room": 1, "time": -1 },
        { 
            name: "chat_room_time_idx",
            background: true
        }
    );
    print("  - Successfully created chat_room_time_idx");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.code === 85) {
        print("  - Index chat_room_time_idx already exists");
    } else {
        print(`  - Error creating index: ${e.message}`);
        throw e;
    }
}

// Index 2: name + time (unique constraint, replaces DynamoDB primary key)
// Ensures no duplicate messages from same user at same timestamp
print("Creating index: name_time_unique_idx");
try {
    collection.createIndex(
        { "name": 1, "time": 1 },
        { 
            name: "name_time_unique_idx",
            unique: true,
            background: true
        }
    );
    print("  - Successfully created name_time_unique_idx");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.code === 85) {
        print("  - Index name_time_unique_idx already exists");
    } else {
        print(`  - Error creating index: ${e.message}`);
        throw e;
    }
}

// Verify indexes
print("");
print("=== Current Indexes ===");
const indexes = collection.getIndexes();
indexes.forEach(function(idx) {
    print(`  - ${idx.name}: ${JSON.stringify(idx.key)}`);
    if (idx.unique) {
        print(`    (unique: true)`);
    }
});

print("");
print("=== Index Creation Complete ===");
