# Stub Translation Service

A minimal HTTP stub that mimics the `hdeu-hub-translation` REST API surface.
All translation requests are acknowledged with success status codes; request
bodies are silently dropped.

This enables a **translation-disabled deployment** where:

- File translations (`postData`) succeed without a real translation service
- Form translations succeed without a real translation service
- Translation callbacks are processed as `COMPLETED` immediately
- The translation status in the database is updated to `COMPLETED`
- Applications can be submitted without waiting for translation
- No third-party translation account is required

## Endpoints

| Method | Path                 | Status | Purpose                     |
|--------|----------------------|--------|-----------------------------|
| POST   | `/translation-service`   | 200    | Form translation request    |
| POST   | `/file-translation-service` | 200 | File translation request    |
| POST   | `/translation`           | 200    | Translation success callback |
| GET    | `/translation`           | 200    | Translation success callback |

All endpoints return `200 OK` with an empty body (or `[]` for GET on known routes).

## Usage

### Deploy with local-scenario.yml (Recommended)

The stub-translation service is included in `hdeu-hub-simulation/local-scenario.yml`.
Simply start the full stack:

```bash
cd /home/villefri/Coding/hdeu/hdeu-hub-simulation
CONTAINERS_CONF=containers.conf podman-compose -f local-scenario.yml up -d --build
```

The stub is automatically built from `../hdeu-translation-stub` and starts
before `hdeu-access` (which is configured to use it).

### Local development (no Docker)

```bash
python3 stub_translation.py [PORT]   # PORT defaults to 8084
```

Then update your service configuration to point to `http://localhost:8084/...`.

## Configuration

### hdeu-access (pre-configured in local-scenario.yml)

The `hdeu-access` service in `local-scenario.yml` is already configured to use the stub:

```yaml
- TRANSLATION_SERVICE_URL=http://stub-translation:8084/translation-service
- TRANSLATION_SERVICE_FILE_URL=http://stub-translation:8084/file-translation-service
- TRANSLATION_SERVICE_CALLBACK_URL=http://stub-translation:8084/translation
- TRANSLATION_SERVICE_X_API_KEY=bc6dba36-e87e-4c27-95ba-ff3777acc703
- ENABLE_TRANSLATION=true
```

### hdeu-hub-repo

To use the stub with hdeu-hub-repo, update `hub-repo/conf/config.json`:

```json
{
  "translation": {
    "translation_service_url": "http://stub-translation:8084/translation-service",
    "callback_url": "http://stub-translation:8084/translation"
  }
}
```

## How It Works

1. When a file is uploaded via `postData`, hdeu-access calls the translation
   service to translate the file.
2. The stub immediately returns `200 OK`, simulating successful translation.
3. The translation service would normally call back to the callback URL when
   translation is complete. The stub accepts the callback and returns `200 OK`.
4. The translation status in the database is updated to `COMPLETED`.
5. The frontend can now submit the application.

## Differences from Real Translation Service

| Aspect              | Real Service          | Stub                     |
|---------------------|-----------------------|--------------------------|
| Translation         | Actual translation    | None (instant success)   |
| Response time       | Seconds to minutes    | Instant                  |
| API key validation  | Required              | Accepted any             |
| Callback handling   | Async, after work     | Synchronous ACK          |
| Error handling      | Real errors           | Never fails              |

## Networks

The stub connects to the same networks as the other services in `local-scenario.yml`:

- `mongo-nw` (mongo-network) - for hdeu-access communication
- `ui-repo-nw` (ui-repo-network) - for hdeu-hub-repo communication
- `proxy-ui-nw` (proxy-ui-network) - for reverse proxy routing

## File Structure

```
hdeu-translation-stub/
├── Dockerfile              # Python 3.11 slim container
├── README.md               # This file
└── stub_translation.py     # The stub HTTP server
```
