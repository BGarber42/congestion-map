# Maps-like Congestion API

This project is designed to be a scalable system for accepting real-time location data from devices and returning congestion information for a given location.

## Architecture

```mermaid
graph TD
    subgraph "Clients"
        A[Device/User]
    end

    subgraph "API Layer (FastAPI)"
        B[POST /ping]
        C[GET /congestion]
    end

    subgraph "Queue (AWS SQS)"
        D{pings-queue}
    end

    subgraph "Processing"
        E[Worker]
    end

    subgraph "Data Store (AWS DYnamoDB)"
        F[(congestion-table)]
    end

    A -- Ping (JSON) --> B
    B -- Queues Ping --> D
    E -- Polls Queue --> D
    E -- Validate/Enrich --> E
    E -- Stores Record --> F
    A -- Query --> C
    C -- Query --> F
    F -- Pings --> C
    C -- Congestion Data --> C
    C -- Returns Info --> A
```

## Running Locally

This project uses `uv` for dependency management. You will also need Docker to run the required AWS services (SQS, DynamoDB) locally using LocalStack.

### Prerequisites

*   Python 3.10+
*   [Docker](https://www.docker.com/products/docker-desktop/)
*   [uv](https://github.com/astral-sh/uv) (`pip install uv`)

### 1. Set up the Environment

First, create a virtual environment and install the dependencies.

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate # (or .\.venv\Scripts\activate.bat on Windows)

# Sync dependencies from uv.lock
uv pip sync
```

### 2. Configure Environment Variables

The application requires environment variables to connect to the local AWS services. Create a file named `.env.dev` in the root of the project with the following content:

```ini
# .env.dev
SQS_ENDPOINT_URL=http://localhost:9324
DYNAMODB_ENDPOINT_URL=http://localhost:8002
AWS_REGION=us-east-1

# Dummy credentials for local services - not used but required by boto3
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

### 3. Start Local AWS Services

In a separate terminal, start the local DynamoDB and SQS services using Docker.

```bash
docker compose up
```

Wait for the services to be ready. You can access the ElasticMQ admin console at http://localhost:9325 to see the queue.

### 4. Run the API Server and Worker

You will need two separate terminals for this step, both with the virtual environment activated.

**Terminal 1: Run the FastAPI API Server**

```bash
# This will also create the SQS queue on startup
uv run uvicorn app.api:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

**Terminal 2: Run the SQS Worker**

```bash
uv run python run_worker.py
```
The worker will start polling the SQS queue for incoming pings to process.

## API Usage Examples

### Ping Endpoint

Send a location ping to the system. The request will be accepted immediately, and the ping will be processed asynchronously by the worker.

```bash
curl -X POST "http://127.0.0.1:8000/ping" \
-H "Content-Type: application/json" \
-d '{
  "device_id": "device-alpha-1",
  "timestamp": "2025-01-01T12:00:00Z",
  "lat": 40.7128,
  "lon": -74.0060
}'
```

### Congestion Endpoint

Retrieve the congestion level for a specific location.

**Query by Coordinates:**

```bash
curl -X GET "http://127.0.0.1:8000/congestion?lat=40.7128&lon=-74.0060"
```

**Query by Coordinates with a different resolution:**

The `resolution` parameter aggregates results into a larger parent area. A lower number means a larger area.

```bash
curl -X GET "http://127.0.0.1:8000/congestion?lat=40.7128&lon=-74.0060&resolution=10"
```

**Query by H3 Hex ID:**

You can also query directly by an H3 hex ID.

```bash
# This hex corresponds to the lat/lon above at resolution 12
curl -X GET "http://127.0.0.1:8000/congestion?h3_hex=8c2a1072595ffff"
```



## Benchmarking

### Load Test Summary: `/` Endpoint

| Metric | 10 RPS | 25 RPS | 50 RPS | 100 RPS | 500 RPS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Timing** | | | | | |
| Mean Query Speed | 18 ms | 23 ms | 40 ms | 53 ms | 83 ms |
| Fastest Query Speed | 6 ms | 6 ms | 8 ms | 10 ms | 8 ms |
| Slowest Query Speed | 29 ms | 43 ms | 92 ms | 118 ms | 221 ms |
| Actual Mean RPS | 12.43 req/sec | 31.03 req/sec | 61.07 req/sec | 122.55 req/sec | 594.56 req/sec |
| **Data & Responses** | | | | | |
| Total Data Transferred | 11 kB | 28 kB | 56 kB | 113 kB | 565 kB |
| Successful Responses (200) | 50 | 125 | 250 | 500 | 2500 |
| Total Test Time | 4022 ms | 4028 ms | 4093 ms | 4079 ms | 4204 ms |



### Load Test Summary: `POST /ping` Endpoint

| Metric | 10 RPS | 25 RPS | 50 RPS | 100 RPS | 500 RPS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Timing** | | | | | |
| Mean Query Speed | 66 ms | 60 ms | 60 ms | 78 ms | 175 ms |
| Fastest Query Speed | 10 ms | 8 ms | 9 ms | 11 ms | 7 ms |
| Slowest Query Speed | 294 ms | 298 ms | 314 ms | 340 ms | 407 ms |
| Actual Mean RPS | 12.44 req/sec | 31.02 req/sec | 59.67 req/sec | 119.76 req/sec | 578.52 req/sec |
| **Data & Responses** | | | | | |
| Total Data Transferred | 22 kB | 55 kB | 106 kB | 220 kB | 1.1 MB |
| Successful Responses (202) | 50 | 125 | 242 | 500 | 2500 |
| Failed / Timed Out Requests | 0 | 0 | **8** | 0 | 0 |
| Total Test Time | 4018 ms | 4029 ms | 4055 ms | 4175 ms | 4321 ms |

### Load Test Summary: `/congestion` Endpoint (Assorted Tests)

| Metric | `/congestion` (Scan) | `/congestion?lat&lon` | `/congestion?lat&lon&res` | `/congestion?h3_hex` (Query) |
| :--- | :--------------------- | :-------------------- | :------------------------ | :--------------------------- |
| **Test Parameters** | | | | |
| Target Throughput | 100 RPS | 500 RPS | 500 RPS | 500 RPS |
| **Timing** | | | | |
| Mean Query Speed | 66 ms | 182 ms | 217 ms | 230 ms |
| Fastest Query Speed | 10 ms | 10 ms | 10 ms | 10 ms |
| Slowest Query Speed | 307 ms | 576 ms | 493 ms | 671 ms |
| Actual Mean RPS | 116.47 req/sec | 532.22 req/sec | 526.74 req/sec | 515.32 req/sec |
| **Data & Responses** | | | | |
| Total Data Transferred | 135 kB | 1.3 MB | 1.4 MB | 1.3 MB |
| Successful Responses (200) | 476 | 5000 | 5000 | 5000 |
| Failed / Timed Out Requests | **24** | 0 | 0 | 0 |
| Total Test Time | 4086 ms | 9394 ms | 9492 ms | 9702 ms |
