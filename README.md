# Amazon DynamoDB Chat Sample

A demonstration application for building a real-time chat system using Amazon DynamoDB and AWS Chalice, showcasing effective use of Global Secondary Indexes (GSI) for efficient query patterns.

![demo](./demo.gif)

## Table of Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
  - [Local Development](#local-development)
  - [AWS Deployment](#aws-deployment)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [DynamoDB Data Model](#dynamodb-data-model)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Architecture

![architecture](./demo_arch.png)

The application uses a serverless architecture with AWS Lambda (via Chalice) serving a REST API backed by DynamoDB. The frontend is a Vue.js single-page application that communicates with the backend via Axios HTTP requests. Messages are stored in DynamoDB with a Global Secondary Index enabling efficient queries by chat room and timestamp.

## Requirements

- Python 3.7 or higher
- AWS CLI configured with appropriate credentials (for AWS deployment)
- Java Runtime Environment (for DynamoDB Local)
- pip (Python package manager)

## Quick Start

### Local Development

1. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

2. **Download and start DynamoDB Local:**

```bash
# Download DynamoDB Local
wget https://s3-us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.tar.gz
tar xzf dynamodb_local_latest.tar.gz

# Start DynamoDB Local (runs on port 8000)
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -port 8000 -inMemory
```

3. **Set up AWS credentials for DynamoDB Local:**

DynamoDB Local requires AWS credentials (they can be any values for local development):

```bash
export AWS_ACCESS_KEY_ID=fakeMyKeyId
export AWS_SECRET_ACCESS_KEY=fakeSecretAccessKey
export AWS_DEFAULT_REGION=us-east-1
```

4. **Create the chat table in DynamoDB Local:**

```bash
aws dynamodb create-table \
    --endpoint-url http://localhost:8000 \
    --table-name chat \
    --attribute-definitions \
        AttributeName=name,AttributeType=S \
        AttributeName=time,AttributeType=S \
        AttributeName=chat_room,AttributeType=S \
    --key-schema \
        AttributeName=name,KeyType=HASH \
        AttributeName=time,KeyType=RANGE \
    --global-secondary-indexes \
        'IndexName=chat_room_time_idx,KeySchema=[{AttributeName=chat_room,KeyType=HASH},{AttributeName=time,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

5. **Set the environment variable and start the Chalice local server:**

```bash
export API_ENDPOINT=localhost
chalice local --stage local --port 8080
```

6. **Access the chat application:**

Open your browser and navigate to `http://localhost:8080/chat`

### AWS Deployment

Deploying to AWS requires IAM permissions for Chalice and DynamoDB. See the [Chalice credentials documentation](https://github.com/aws/chalice#credentials) for details.

1. **Create the DynamoDB table in AWS:**

```bash
aws dynamodb create-table \
    --table-name chat \
    --attribute-definitions \
        AttributeName=name,AttributeType=S \
        AttributeName=time,AttributeType=S \
        AttributeName=chat_room,AttributeType=S \
    --key-schema \
        AttributeName=name,KeyType=HASH \
        AttributeName=time,KeyType=RANGE \
    --global-secondary-indexes \
        'IndexName=chat_room_time_idx,KeySchema=[{AttributeName=chat_room,KeyType=HASH},{AttributeName=time,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

2. **Deploy the application:**

```bash
chalice deploy
```

After deployment, you will see output similar to:

```
Resources deployed:
  - Lambda ARN: arn:aws:lambda:REGION:ACCOUNT_ID:function:dynamodb-python-chat-sample-dev
  - Rest API URL: https://XXXXXXXXXX.execute-api.REGION.amazonaws.com/api/
```

3. **Update the API endpoint configuration:**

Edit `.chalice/config.json` and set the `API_ENDPOINT` for the `dev` stage to your deployed API Gateway URL:

```json
{
  "stages": {
    "dev": {
      "environment_variables": {
        "API_ENDPOINT": "https://XXXXXXXXXX.execute-api.REGION.amazonaws.com/api/"
      }
    }
  }
}
```

4. **Redeploy to apply the configuration:**

```bash
chalice deploy
```

5. **Access the deployed application:**

Navigate to `https://XXXXXXXXXX.execute-api.REGION.amazonaws.com/api/chat`

## Project Structure

```
amazon-dynamodb-chat-sample/
├── app.py                    # Main Chalice application with API routes
├── chalicelib/
│   ├── ddb.py               # DynamoDB operations (DdbChat class)
│   └── livechat.html        # Vue.js frontend application
├── .chalice/
│   ├── config.json          # Chalice configuration for stages
│   └── policy-dev.json      # IAM policy for dev deployment
├── tests/
│   ├── conftest.py          # pytest fixtures and DynamoDB setup
│   └── test_app.py          # API endpoint tests
├── requirements.txt          # Python dependencies
├── test_requirements.txt     # Testing dependencies
├── demo_arch.png            # Architecture diagram
├── table.png                # DynamoDB table structure visualization
├── GSI_sample.png           # GSI structure visualization
└── amazon_dynamodb_chat_sample.json  # Sample data for NoSQL Workbench
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check endpoint |
| GET | `/chat` | Serves the chat client HTML interface |
| POST | `/chat/comments/add` | Add a new chat message |
| GET | `/chat/comments/latest` | Get the 20 most recent messages |
| GET | `/chat/comments/all` | Get all messages in the chat room |
| GET | `/chat/comments/latest/{seq_id}` | Get messages newer than the specified timestamp |

### Adding a Comment

```bash
curl -X POST http://localhost:8080/chat/comments/add \
  -H "Content-Type: application/json" \
  -d '{"name": "user1", "comment": "Hello, world!"}'
```

### Getting Latest Comments

```bash
curl http://localhost:8080/chat/comments/latest
```

## DynamoDB Data Model

The application uses a single table design with a Global Secondary Index for efficient querying.

**Primary Table:**

| Attribute | Type | Key |
|-----------|------|-----|
| name | String | Partition Key (PK) |
| time | String (microsecond Unix timestamp) | Sort Key (SK) |
| comment | String | - |
| chat_room | String | - |

**Global Secondary Index (chat_room_time_idx):**

| Attribute | Type | Key |
|-----------|------|-----|
| chat_room | String | Partition Key |
| time | String | Sort Key |

The GSI enables efficient queries for all messages in a chat room, sorted by time.

![table](./table.png)

![GSI_sample](./GSI_sample.png)

## Testing

Tests require DynamoDB Local running on port 8000. The test suite will automatically create and tear down the required table.

```bash
# Start DynamoDB Local (in a separate terminal)
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -port 8000 -inMemory

# Run tests
export API_ENDPOINT=localhost
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test_user
export AWS_SECRET_ACCESS_KEY=test_key
pytest -vv
```

### Linting

```bash
flake8 .
```

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

When contributing:
1. Fork the repository
2. Create a feature branch
3. Ensure tests pass locally
4. Submit a pull request

For bug reports and feature requests, please use the GitHub issue tracker.

## License

This project is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.

---

*Originally written and maintained by contributors and [Devin](https://app.devin.ai), with updates from the core team.*
