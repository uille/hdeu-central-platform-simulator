# hdeu-dispatcher-stub

## Overview

**hdeu-dispatcher-stub** is a minimal HTTP stub server that mimics the [hdeu-dispatcher](../hdeu-dispatcher/README.md) REST API surface. It acknowledges all requests with the correct HTTP status codes while silently discarding all payloads.

This module enables a **dispatcher-disabled deployment** of the EU Health Data (HD-EU) Central Platform where:

- Catalogue operations (create/update/delete) succeed without a real dispatcher
- Application dispatch requests are ACKed but never forwarded to national gateways
- Domibus messaging is entirely bypassed
- Dataset metadata is managed directly via the hub-repo API
- Application status is managed directly via the hdeu-access REST API

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
    ├── POST /api/data-request-application → hdeu-access (MongoDB insert)
    │       │
    │       └── Application stored with status="PENDING"
    │       (scheduler never fires due to large intervals)
    │
    ▼
hdeu-access (backend)
    │
    ├── Catalogue create/update/delete
    │       │
    │       ├── DispatcherClient.createCatalogueMap() → stub-dispatcher:5100
    │       │       └── Returns 201 Created (ACKed, payload dropped)
    │       │
    │       └── DispatcherClient.updateCatalogueMap() → stub-dispatcher:5100
    │               └── Returns 200 OK (ACKed, payload dropped)
    │
    ▼
stub-dispatcher
    │
    ├── ACKs all requests with correct HTTP status codes
    ├── Silently drops all request bodies
    └── Never forwards anything to Domibus or national gateways
```

## Deployment Scenarios

### Scenario 1: Full Dispatcher-Disabled (Recommended)

Use the stub + disabled schedulers. All catalogue and application operations succeed locally. No cross-border messaging.

```yaml
# In local-scenario.yml or your compose file
services:
  stub-dispatcher:
    build: ../hdeu-dispatcher-stub
    container_name: stub-dispatcher
    ports: ["5100:5100"]
    networks: [mongo-network, ui-repo-network, proxy-ui-network]

  hdeu-access:
    environment:
      - DISPATCHER_URL=http://stub-dispatcher:5100
      - OUTGOING_APPLICATION_ACTIVITIES_ENABLE=0
      - DATA_ACCESS_DISPATCHER_INTERVAL=999999999
      - DATA_REQUEST_DISPATCHER_INTERVAL=999999999
      # ... (see complete configuration above)
```

### Scenario 2: Selective Dispatcher (Production + Stub for ITB)

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

### Expected responses

```
# POST /catalogs → 201 Created (no body)
# GET /catalogs → 200 OK, body: []
# POST /data-permit/create/application → 201 Created (no body)
# POST /application/activity → 201 Created (no body)
# DELETE /catalogs/{id} → 200 OK (no body)
```

## Limitations

- **No SOAP/AS4 support:** The stub does not implement the Domibus SOAP web service (`BackendInterface`). If any component expects to receive SOAP messages from Domibus, this stub cannot handle them.
- **No message persistence:** All request bodies are silently discarded. Nothing is stored or forwarded.
- **No authentication:** The stub accepts requests with any API key. This is intentional for the dispatcher-disabled use case.
- **No health check endpoint:** The stub does not implement a `/health` endpoint. If a health check is required, add one to the handler.

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
