#!/usr/bin/env python3
"""
Stub Dispatcher - ACKs and callbacks to hdeu-access.

A minimal HTTP server that mimics the hdeu-dispatcher REST API surface
so that hdeu-access believes the dispatcher is operational. All requests
are acknowledged with the correct HTTP status code. Additionally, when
a data access application is received via POST /data-permit/create/application,
the stub simulates the full dispatcher lifecycle by:

1. ACKing the create request with 201 Created
2. Simulating processing delay
3. Callback to hdeu-access via POST /dispatcher/status with status
   "domibus_national_received" so the application is marked as dispatched

This enables a dispatcher-enabled simulation where the full call flow
works end-to-end without a real Domibus backend.

Usage:
    python3 stub_dispatcher.py [PORT]       # PORT defaults to 5100

Docker:
    docker compose up -d --build
"""

import json
import logging
import os
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from urllib import request as urllib_request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [stub-dispatcher] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stub-dispatcher")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
# URL of hdeu-access service (e.g. http://hdeu-access:8080 inside Docker)
HEALTH_DATA_ACCESS_URL = os.environ.get(
    "HEALTH_DATA_ACCESS_URL", "http://hdeu-access:8080"
)
# API key that hdeu-access expects from the dispatcher
HEALTH_DATA_ACCESS_API_KEY = os.environ.get(
    "HEALTH_DATA_ACCESS_API_KEY", "c0107b96-78a1-408e-b05f-a65eb3a3d0a8"
)
# Delay (seconds) before simulating the dispatcher callback
CALLBACK_DELAY_SECONDS = int(os.environ.get("CALLBACK_DELAY_SECONDS", "2"))

# In-memory store for received applications: { data_permit_id: { ... } }
received_applications = {}
_lock = threading.Lock()


class StubDispatcherHandler(BaseHTTPRequestHandler):
    """Acknowledges requests and always callbacks to hdeu-access for application creation."""

    # Routes mapped to their expected HTTP status codes.
    # These match what DispatcherClient checks in hdeu-access.
    ROUTE_STATUS = {
        "POST": {
            "/data-permit/create/application": 201,
            "/data-permit/delete": 204,
            "/application/activity": 201,
            "/catalogs": 201,
        },
        "PUT": {
            "/catalogs/": 200,
            "/data-permit/applications/": 200,
        },
        "DELETE": {
            "/catalogs/": 200,
            "/data-permit/delete": 204,
        },
        "GET": {
            "/catalogs": 200,
            "/catalog/catalogId/": 200,
        },
    }

    def _route_key(self) -> str:
        """Normalize the request path for route matching."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # Normalize path parameters so /catalogs/{id} matches /catalogs/
        if path.startswith("/catalogs/") and len(path.split("/")) > 3:
            path = "/catalogs/"
        if path.startswith("/data-permit/applications/") and len(path.split("/")) > 4:
            path = "/data-permit/applications/"
        if path.startswith("/catalog/catalogId/") and len(path.split("/")) > 4:
            path = "/catalog/catalogId/"

        return path

    def _get_response_code(self) -> int:
        """Determine the response status code for this request."""
        path = self._route_key()
        method = self.command
        for m, routes in self.ROUTE_STATUS.items():
            if m == method:
                for route, code in routes.items():
                    if path == route or path.startswith(route):
                        return code
        # Fallback for any unrecognized route
        return 200

    def _read_body(self) -> bytes:
        """Consume and return the request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return b""

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger with a consistent prefix."""
        log.info("%s %s", self.client_address[0], format % args)

    # ── HTTP method handlers ────────────────────────────────────────────

    def do_GET(self):
        log.info("do_GET %s", self.path)
        self._read_body()
        code = self._get_response_code()
        # GET /catalogs must return [] (not 404) - DispatcherClient treats 404 as failure.
        body = b"[]" if self.path == "/catalogs" else b'{"result_message":"ok"}'
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        log.info("do_POST %s", self.path)
        body = self._read_body()
        code = self._get_response_code()

        # Handle /data-permit/create/application with callback logic
        if self.path == "/data-permit/create/application":
            self._handle_create_application(body, code)
        else:
            # For all other POST routes, just ACK
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _handle_create_application(self, body: bytes, ack_code: int) -> None:
        """ACK the create request and schedule a callback to hdeu-access."""
        # Parse the application body to extract needed fields
        application_data = None
        try:
            application_data = json.loads(body) if body else {}
        except (json.JSONDecodeError, TypeError):
            application_data = {}

        # Generate a data_permit_id
        data_permit_id = str(uuid.uuid4())

        # Extract application_id
        application_id = application_data.get("application_id", "")

        # Extract catalog_ids from the application
        catalog_ids = self._extract_catalog_ids(application_data)

        # Build response body matching DispatchResponse schema (JSON array)
        # DispatchResponse: type=array, items={application_id, status, catalog_ids, data_permit_id, application_type}
        # hdeu-access DispatcherScheduledJob.markDispatcherRecordAsCompleted expects JsonArray
        response_body = json.dumps([{
            "application_id": application_id,
            "status": "dispatcher_received",
            "catalog_ids": catalog_ids,
            "data_permit_id": data_permit_id,
            "application_type": "DATA_ACCESS_APPLICATION",
        }]).encode("utf-8")

        # ACK immediately with response body
        self.send_response(ack_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

        # Store the received application for debugging / inspection
        with _lock:
            received_applications[data_permit_id] = {
                "application_id": application_id,
                "catalog_ids": catalog_ids,
                "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "raw_body": body.decode("utf-8", errors="replace")[:500],
            }

        log.info(
            "Scheduled callback for application_id=%s, data_permit_id=%s, catalog_ids=%s",
            application_id,
            data_permit_id,
            catalog_ids,
        )

        # Schedule the callback in a background thread
        callback_data = {
            "application_id": application_id,
            "data_permit_id": data_permit_id,
            "catalog_ids": catalog_ids,
        }
        timer = threading.Timer(CALLBACK_DELAY_SECONDS, self._send_callback, args=[callback_data])
        timer.daemon = True
        timer.start()

    def _extract_catalog_ids(self, app_data: dict) -> list:
        """Extract catalog IDs from the application data."""
        # Try different possible locations for catalog IDs
        if "catalog_ids" in app_data:
            ids = app_data["catalog_ids"]
            if isinstance(ids, list):
                return [str(i) for i in ids if i]
            elif ids:
                return [str(ids)]

        if "catalogs" in app_data:
            catalogs = app_data["catalogs"]
            if isinstance(catalogs, list):
                return [
                    str(c.get("catalog_id", c.get("id", "")))
                    for c in catalogs
                    if c.get("catalog_id") or c.get("id")
                ]

        if "datasets" in app_data:
            datasets = app_data["datasets"]
            if isinstance(datasets, list):
                ids = []
                for ds in datasets:
                    if isinstance(ds, dict):
                        cid = ds.get("catalog_id", ds.get("catalogue_id", ""))
                        if cid and cid not in ids:
                            ids.append(str(cid))
                return ids

        # Fallback: generate a placeholder catalog_id
        return [str(uuid.uuid4())]

    def _send_callback(self, callback_data: dict) -> None:
        """Send the status callback to hdeu-access."""
        application_id = callback_data["application_id"]
        data_permit_id = callback_data["data_permit_id"]
        catalog_ids = callback_data["catalog_ids"]

        # Build the callback payload matching DispatcherMessage schema
        callback_payload = [{
            "application_id": application_id,
            "status": "domibus_national_received",
            "data_permit_id": data_permit_id,
            "catalog_ids": catalog_ids,
        }]

        callback_url = HEALTH_DATA_ACCESS_URL.rstrip("/") + "/dispatcher/status"
        payload_bytes = json.dumps(callback_payload).encode("utf-8")

        log.info(
            "Sending callback to hdeu-access: %s",
            callback_url,
        )
        log.info(
            "Callback payload: %s",
            callback_payload,
        )

        try:
            req = urllib_request.Request(
                callback_url,
                data=payload_bytes,
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("Content-Length", str(len(payload_bytes)))
            req.add_header("X-API-Key", HEALTH_DATA_ACCESS_API_KEY)

            with urllib_request.urlopen(req, timeout=10) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                log.info(
                    "Callback succeeded: status=%d, body=%s",
                    status,
                    body,
                )
        except Exception as e:
            log.error("Callback failed: %s", e)

    def do_PUT(self):
        log.info("do_PUT %s", self.path)
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        log.info("do_DELETE %s", self.path)
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5100
    log.info("Stub dispatcher listening on port %d", port)
    log.info("Callback URL: %s", HEALTH_DATA_ACCESS_URL)
    log.info("Callback delay: %d seconds", CALLBACK_DELAY_SECONDS)
    HTTPServer(("0.0.0.0", port), StubDispatcherHandler).serve_forever()
