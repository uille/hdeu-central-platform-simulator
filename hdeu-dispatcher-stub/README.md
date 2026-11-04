# hdeu-dispatcher-stub

## Overview

**hdeu-dispatcher-stub** is a minimal HTTP stub server that mimics the [hdeu-dispatcher](../hdeu-dispatcher/README.md) REST API surface. It acknowledges all requests with the correct status codes and simulates the full dispatcher callback lifecycle.

When `POST /data-permit/create/application` is received:

1. The stub ACKs with `201 Created`
2. After a configurable delay (default: 2 seconds), the stub calls back to hdeu-access
3. The callback is `POST /dispatcher/status` with status `"domibus_national_received"`
4. hdeu-access updates the application's catalog status from `SENT` to `SUBMITTED`

This enables end-to-end testing of the dispatching workflow without a real Domibus backend.

## How It Works

The stub implements the exact HTTP endpoints that `DispatcherClient` in `hdeu-access` calls, returning the status codes that `DispatcherClient` expects for success:

| Method | Endpoint | Status Code | Called By |
|--------|----------|-------------|-----------|
| `POST` | `/data-permit/create/application` | `201 Created` | `DispatcherClient.createApplication()` |
| `DELETE` | `/data-permit/delete` | `204 No Content` | `DispatcherClient.deleteApplications()` |
| `PUT` | `/data-permit/applications/{id}` | `200 OK` | `DispatcherClient.updateApplication()` |
| `POST` | `/catalogs` | `201 Created` | `DispatcherClient.createCatalogueMap()` |
| `PUT` | `/catalogs/{id}` | `200 OK` | `DispatcherClient.updateCatalogueMap()` |
| `DELETE` | `/catalogs/{id}` | `200 OK` | `DispatcherClient.deleteCatalogMappingByMongoId()` |
| `GET` | `/catalogs` | `200 OK` (returns `[]`) | `DispatcherClient.getAllCatalogueMap()` |
| `GET` | `/catalog/catalogId/{id}` | `200 OK` | `DispatcherClient.getCatalogMappingByCatalogId()` |
| `POST` | `/application/activity` | `201 Created` | `DispatcherClient.sendOutgoingActivity()` |

**Critical detail:** `GET /catalogs` returns `[]` (empty JSON array) instead of `404`. The `DispatcherClient` treats `404` as a failure, so the stub must return `200 OK` with a valid response.

## Quick Start

### Running locally

```bash
python3 stub_dispatcher.py [PORT]
# PORT defaults to 5100
```

### Running with Docker

```bash
docker compose up -d --build
```

## Integration with hdeu-access

To use the stub, configure `hdeu-access` to point to it and disable the dispatcher schedulers.

### Environment Variables for hdeu-access

#### Dispatcher Connection

| Variable | Value | Description |
|----------|-------|-------------|
| `DISPATCHER_URL` | `http://stub-dispatcher:5100` | URL of the stub dispatcher (or any ACK-only dispatcher) |
| `DISPATCHER_X_API_KEY` | `47173bdf-bba8-436c-912c-ad12be97ba34` | API key accepted by the stub (any value works) |

#### Scheduler Intervals (Disable Background Dispatching)

These environment variables control the periodic schedulers that poll for pending applications and forward them to the dispatcher. Set them to very large values to effectively disable the schedulers. The stub ACKs requests but nothing is actually forwarded.

| Variable | Default | Disabled Value | Description |
|----------|---------|----------------|-------------|
| `OUTGOING_APPLICATION_ACTIVITIES_ENABLE` | `1` | `0` | **Primary switch** - Disables the outgoing application activities scheduler entirely |
| `DATA_ACCESS_DISPATCHER_INTERVAL` | `60000` | `999999999` | Interval (ms) for data access application dispatcher |
| `DATA_REQUEST_DISPATCHER_INTERVAL` | `60000` | `999999999` | Interval (ms) for data request application dispatcher |
| `DATA_ACCESS_DISPATCHER_FOR_SENT_APPLICATIONS_INTERVAL` | `60000` | `999999999` | Interval (ms) for polling sent data access application statuses |

### Stub Dispatcher Environment Variables

The stub dispatcher can be configured with these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CALLBACK_DELAY_SECONDS` | `2` | Delay in seconds before sending the callback to hdeu-access. Simulates processing time. |
| `HEALTH_DATA_ACCESS_URL` | `http://hdeu-access:8080` | URL of the hdeu-access service. Used for the callback endpoint. |
| `HEALTH_DATA_ACCESS_API_KEY` | `c0107b96-78a1-408e-b05f-a65eb3a3d0a8` | API key sent in `X-API-Key` header for the callback to hdeu-access. |
| `DATA_REQUEST_DISPATCHER_FOR_SENT_APPLICATIONS_INTERVAL` | `60000` | `999999999` | Interval (ms) for polling sent data request application statuses |
| `WITHDRAW_DISPATCHER_INTERVAL` | `86400000` | `999999999` | Interval (ms) for withdraw application scheduler |
| `WITHDRAW_THRESHOLD_DAYS` | `28` | `9999` | Threshold (days) for withdraw eligibility |
| `ADDITIONAL_INFO_WITHDRAW_THRESHOLD_DAYS` | `28` | `9999` | Threshold (days) for additional info withdraw |

#### Retries (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_ACCESS_DISPATCHER_MAX_RETRIES` | `10` | Max retries for data access applications |
| `DATA_REQUEST_DISPATCHER_MAX_RETRIES` | `10` | Max retries for data request applications |
| `DATA_ACCESS_DISPATCHER_FOR_SENT_APPLICATIONS_MAX_RETRIES` | `10` | Max retries for polling sent data access statuses |
| `DATA_REQUEST_DISPATCHER_FOR_SENT_APPLICATIONS_MAX_RETRIES` | `10` | Max retries for polling sent data request statuses |
| `WITHDRAW_DISPATCHER_MAX_RETRIES` | `5` | Max retries for withdraw operations |

#### Other hdeu-access Configuration

| Variable | Description |
|----------|-------------|
| `HUB_REPO_URL` | URL of the hub-repo service |
| `HUB_REPO_X_API_KEY` | API key for hub-repo |
| `HUB_STORE_UPLOAD_DATA_URL` | URL of the hub-store service |
| `PIVEAU_STORE_API_KEY` | API key for hub-store |

### Complete hdeu-access Environment Configuration

```yaml
hdeu-access:
  environment:
    # ── Stub dispatcher connection ──
    - DISPATCHER_URL=http://stub-dispatcher:5100
    - DISPATCHER_X_API_KEY=47173bdf-bba8-436c-912c-ad12be97ba34

    # ── Disable all dispatcher schedulers ──
    - OUTGOING_APPLICATION_ACTIVITIES_ENABLE=0
    - DATA_ACCESS_DISPATCHER_INTERVAL=999999999
    - DATA_REQUEST_DISPATCHER_INTERVAL=999999999
    - DATA_ACCESS_DISPATCHER_FOR_SENT_APPLICATIONS_INTERVAL=999999999
    - DATA_REQUEST_DISPATCHER_FOR_SENT_APPLICATIONS_INTERVAL=999999999
    - WITHDRAW_DISPATCHER_INTERVAL=999999999
    - WITHDRAW_THRESHOLD_DAYS=9999
    - ADDITIONAL_INFO_WITHDRAW_THRESHOLD_DAYS=9999

    # ── Hub services ──
    - HUB_REPO_URL=http://hdeu-hub-repo:8080
    - HUB_REPO_X_API_KEY=7c6a7c98-20e1-4915-ba0c-985b6724560b
    - HUB_STORE_UPLOAD_DATA_URL=http://hdeu-hub-store:8080
    - PIVEAU_STORE_API_KEY=0e3296cb-5106-4d77-9e9d-25ef9b6eac71
```

## Architecture

```
hdeu-hub-ui (frontend)
    │
    └── User submits application (status → SUBMITTED)
    │
    ▼
hdeu-access (backend)
    │
    ├── 1. Save application to DATA_ACCESS_APPLICATION collection
    │       (status = ON_GOING)
    │
    ├── 2. Save to DISPATCHER collection
    │       (configuration.status = "pending")
    │
    ├── 3. Scheduled job picks up pending records
    │       (every DATA_ACCESS_DISPATCHER_INTERVAL ms)
    │
    └── 4. POST /data-permit/create/application
            → stub-dispatcher:5100
                │
                ├── Returns 201 Created (ACK)
                │
                └── After CALLBACK_DELAY_SECONDS:
                    │
                    ▼
            hdeu-access:8080/dispatcher/status
                │
                ├── POST with X-API-Key header
                ├── Body: {
                │     "application_id": "...",
                │     "status": "domibus_national_received",
                │     "data_permit_id": "...",
                │     "catalog_ids": ["..."]
                │   }
                │
                └── hdeu-access updates catalog status:
                    SENT → SUBMITTED
                    (application is now "dispatched")
```

## Deployment Scenarios

### Scenario 1: Stub Dispatcher (End-to-End Simulation)

Use the stub to simulate the full dispatcher lifecycle. Applications are dispatched and the stub calls back to hdeu-access.

```yaml
# In local-scenario.yml or your compose file
services:
  stub-dispatcher:
    build: ../hdeu-dispatcher-stub
    container_name: stub-dispatcher
    ports: ["5100:5100"]
    networks: [mongo-network, ui-repo-network, proxy-ui-network]
    environment:
      - CALLBACK_DELAY_SECONDS=2
      - HEALTH_DATA_ACCESS_URL=http://hdeu-access:8080
      - HEALTH_DATA_ACCESS_API_KEY=c0107b96-78a1-408e-b05f-a65eb3a3d0a8

  hdeu-access:
    environment:
      - DISPATCHER_URL=http://stub-dispatcher:5100
      # Keep schedulers enabled (or use reasonable intervals)
      - DATA_ACCESS_DISPATCHER_INTERVAL=5000
      # ... other hdeu-access config
```

### Scenario 2: Selective Dispatcher (Production + Stub for ITB)

Use a real dispatcher for production catalogues and the stub for ITB/test catalogues. This requires catalogue-specific routing logic in the dispatcher itself (not the stub).

Use a real dispatcher for production catalogues and the stub for ITB/test catalogues. This requires catalogue-specific routing logic in the dispatcher itself (not the stub).

## Testing

### Manual testing

```bash
# Start the stub
python3 stub_dispatcher.py 5100 &

# Test catalogue creation (expect 201)
curl -X POST http://localhost:5100/catalogs \
  -H "Content-Type: application/json" \
  -d '{"catalogId":"test-id","recipient":"test_ap","isProduction":true}' \
  -w "\nHTTP Status: %{http_code}\n"

# Test catalogue listing (expect 200 with [])
curl -X GET http://localhost:5100/catalogs \
  -w "\nHTTP Status: %{http_code}\n"

# Test application creation (expect 201)
curl -X POST http://localhost:5100/data-permit/create/application \
  -H "Content-Type: application/json" \
  -d '{"application_id":"test","status":"submitted"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Test application activity (expect 201)
curl -X POST http://localhost:5100/application/activity \
  -H "Content-Type: application/json" \
  -d '{"type":"application","operation":"decision","objectId":"test","payload":{}}' \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Testing with callback

The stub always sends a callback to hdeu-access after receiving `POST /data-permit/create/application`. You can verify the callback by:

1. Starting hdeu-access with the dispatcher schedulers enabled
2. Submitting an application through the UI
3. Watching the logs for the callback:
   ```
   [stub-dispatcher] INFO Scheduled callback for application_id=..., data_permit_id=..., catalog_ids=[...]
   [stub-dispatcher] INFO Sending callback to hdeu-access: http://hdeu-access:8080/dispatcher/status
   [stub-dispatcher] INFO Callback succeeded: status=200, body={"result_message":"ok"}
   ```

4. Checking that the application's catalog status has changed from `SENT` to `SUBMITTED` in the MongoDB `DATA_ACCESS_APPLICATION` collection.

### Expected responses

```
# POST /catalogs → 201 Created (no body)
# GET /catalogs → 200 OK, body: []
# POST /data-permit/create/application → 201 Created, body: [{"application_id":"...","status":"dispatcher_received","catalog_ids":["..."],"data_permit_id":"...","application_type":"DATA_ACCESS_APPLICATION"}]
# POST /application/activity → 201 Created (no body)
# DELETE /catalogs/{id} → 200 OK (no body)
```

## Limitations

- **No SOAP/AS4 support:** The stub does not implement the Domibus SOAP web service (`BackendInterface`). If any component expects to receive SOAP messages from Domibus, this stub cannot handle them.
- **In-memory storage only:** Received applications are stored in memory and lost on restart. This is intentional for the dispatcher simulation use case.
- **No authentication:** The stub accepts requests with any API key. This is intentional for the dispatcher simulation use case.
- **No health check endpoint:** The stub does not implement a `/health` endpoint. If a health check is required, add one to the handler.
- **Callback requires network access:** The stub must be able to reach hdeu-access at `HEALTH_DATA_ACCESS_URL`. Ensure both services are on the same Docker network.

## Files

```
hdeu-dispatcher-stub/
├── README.md              # This file
├── stub_dispatcher.py     # Python stub server (zero dependencies)
├── Dockerfile             # Docker build file
└── docker-compose.yml     # Docker Compose service definition
```

## License

European Union Public Licence, Version 1.2 (EUPL-1.2)
