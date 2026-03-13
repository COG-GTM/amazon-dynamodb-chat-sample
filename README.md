# Amazon DynamoDB Chat Sample

![codebuild](https://codebuild.ap-northeast-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiL1RBME9sdkZScDFhMjc4M1NhTE1JK3VjUVppaXZURzdRb3dwaXRmVktDWkR4Sy9pMEppcGczU2JnNDVldHg1RkZsaHNCTno4Z2UwWmNmNzBKKzRYdjRBPSIsIml2UGFyYW1ldGVyU3BlYyI6InI1UXVGUFBPYzFJMkJTSDQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)

A real-time chat application built with [AWS Chalice](https://github.com/aws/chalice) and Amazon DynamoDB, demonstrating effective use of DynamoDB access patterns and Global Secondary Indexes (GSI).

![demo](./demo.gif)

## Architecture

![architecture](./demo_arch.png)

The application consists of:

- **Frontend** -- A Vue.js-based chat interface (`chalicelib/livechat.html`) with real-time updates via polling
- **Backend** -- An AWS Chalice application (`app.py`) exposing REST API endpoints through API Gateway and AWS Lambda
- **Data Store** -- An Amazon DynamoDB `chat` table with a GSI (`chat_room_time_idx`) for efficient queries by chat room

## Prerequisites

- Python 3.7.3+
- AWS CLI configured with appropriate credentials
- [AWS Chalice](https://github.com/aws/chalice) (`pip install chalice`)
- Java 8+ (required for DynamoDB Local)
- [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) (for local development)

## Project Structure

```
├── app.py                          # Chalice application entry point and API routes
├── chalicelib/
│   ├── ddb.py                      # DynamoDB data access layer (DdbChat class)
│   └── livechat.html               # Vue.js chat frontend
├── .chalice/
│   ├── config.json                 # Chalice environment and deployment configuration
│   └── policy-dev.json             # IAM permissions for the dev stage
├── tests/
│   ├── conftest.py                 # pytest fixtures (DynamoDB table setup/teardown)
│   └── test_app.py                 # API endpoint integration tests
├── .github/workflows/
│   └── pythonpackage.yml           # GitHub Actions CI (lint, test with DynamoDB Local)
├── requirements.txt                # Production dependencies
├── test_requirements.txt           # Test dependencies
├── setup.cfg                       # flake8 and pytest configuration
└── buildspec.yaml                  # AWS CodeBuild specification
```

## DynamoDB Table Setup

The application uses a `chat` table with a composite primary key (`name`, `time`) and a Global Secondary Index for querying by chat room.

### DynamoDB Local

```bash
aws dynamodb create-table \
    --endpoint-url http://localhost:8000 \
    --table-name chat \
    --attribute-definitions \
        AttributeName=name,AttributeType=S \
        AttributeName=time,AttributeType=S \
        AttributeName=chat_room,AttributeType=S \
    --key-schema \
        KeyType=HASH,AttributeName=name \
        KeyType=RANGE,AttributeName=time \
    --global-secondary-indexes \
        'IndexName=chat_room_time_idx,KeySchema=[{AttributeName=chat_room,KeyType=HASH},{AttributeName=time,KeyType=RANGE}],ProvisionedThroughput={ReadCapacityUnits=1,WriteCapacityUnits=1},Projection={ProjectionType=ALL}' \
    --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1
```

### AWS DynamoDB (Production)

```bash
aws dynamodb create-table \
    --table-name chat \
    --attribute-definitions \
        AttributeName=name,AttributeType=S \
        AttributeName=time,AttributeType=S \
        AttributeName=chat_room,AttributeType=S \
    --key-schema \
        KeyType=HASH,AttributeName=name \
        KeyType=RANGE,AttributeName=time \
    --global-secondary-indexes \
        'IndexName=chat_room_time_idx,KeySchema=[{AttributeName=chat_room,KeyType=HASH},{AttributeName=time,KeyType=RANGE}],ProvisionedThroughput={ReadCapacityUnits=1,WriteCapacityUnits=1},Projection={ProjectionType=ALL}' \
    --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1
```

## Local Development

Setting the `API_ENDPOINT` environment variable to `localhost` tells the application to connect to DynamoDB Local instead of AWS DynamoDB.

1. **Start DynamoDB Local:**

   ```bash
   java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -port 8000 -inMemory
   ```

2. **Set the environment variable:**

   ```bash
   export API_ENDPOINT=localhost
   ```

3. **Create the DynamoDB table** (see [DynamoDB Local](#dynamodb-local) above).

4. **Start the Chalice local server:**

   ```bash
   chalice local --stage local --port 8080
   ```

   The chat application will be available at `http://localhost:8080/chat`.

## Production Deployment

This operation requires IAM permissions for Chalice deployment and DynamoDB access. See the [Chalice credentials documentation](https://github.com/aws/chalice#credentials) for details.

### Step 1: Initial Chalice Deploy

```bash
chalice deploy
```

### Step 2: Note the Generated API Gateway URL

After the first deploy, the CLI output will look like this:

```
INFO:Found credentials in shared credentials file: ~/.aws/credentials
Updating policy for IAM role: dynamodb-python-chat-sample-dev-api_handler
Updating lambda function: dynamodb-python-chat-sample-dev
Updating rest API
Resources deployed:
  - Lambda ARN: arn:aws:lambda:ap-northeast-1:YOUR_AWS_ACCOUNT_ID:function:dynamodb-python-chat-sample-dev
  - Rest API URL: https://YOUR_APIGW_ENDPOINT.execute-api.ap-northeast-1.amazonaws.com/api/
```

### Step 3: Update the API Endpoint Configuration

In `.chalice/config.json`, replace the placeholder `API_ENDPOINT` value with the actual API Gateway URL from Step 2:

```json
"dev": {
    "environment_variables": {
        "API_ENDPOINT": "https://YOUR_APIGW_ENDPOINT.execute-api.ap-northeast-1.amazonaws.com/api/"
    }
}
```

### Step 4: Redeploy with the Updated Configuration

```bash
chalice deploy
```

## Testing

Tests use DynamoDB Local and are run with `pytest`. The test suite automatically creates and tears down the `chat` table, so **pytest must be run without an existing `chat` table** -- otherwise, the tests will fail.

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Set required environment variables
export API_ENDPOINT=localhost
export AWS_DEFAULT_REGION=ap-northeast-1
export AWS_ACCESS_KEY_ID=test_user
export AWS_SECRET_ACCESS_KEY=test_key

# Run tests
pytest -vv
```

### Linting

```bash
flake8 .
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/chat` | Serves the chat client HTML interface |
| `POST` | `/chat/comments/add` | Adds a new chat message |
| `GET` | `/chat/comments/latest` | Returns the 20 most recent messages |
| `GET` | `/chat/comments/all` | Returns all messages in the chat room |
| `GET` | `/chat/comments/latest/{latest_seq_id}` | Returns messages newer than the given sequence ID |

### `POST /chat/comments/add`

**Request body:**

```json
{
    "name": "oranie",
    "comment": "hello world"
}
```

**Response:**

```json
{
    "state": "Commment add OK",
    "time": "1234567890.123456"
}
```

## Data Model

### Primary Table (`chat`)

| name (PK) | time (SK) | comment | chat_room |
|---|---|---|---|
| string | string (microsecond Unix timestamp) | string | string |

### Global Secondary Index (`chat_room_time_idx`)

| chat_room (PK) | time (SK) | comment | name |
|---|---|---|---|
| string | string (microsecond Unix timestamp) | string | string |

### NoSQL Workbench Captures

![table](./table.png)

![table_sample](./table_sample.png)

![GSI_sample](./GSI_sample.png)

Sample data for NoSQL Workbench is available in `amazon_dynamodb_chat_sample.json`.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
