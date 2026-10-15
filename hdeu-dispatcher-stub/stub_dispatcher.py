#!/usr/bin/env python3
"""
Stub Dispatcher - ACKs everything, drops all payloads.

A minimal HTTP server that mimics the hdeu-dispatcher REST API surface
so that hdeu-access believes the dispatcher is operational. All requests
are acknowledged with the correct HTTP status code; request bodies and
responses are silently discarded.

This enables a dispatcher-disabled deployment where:
  - Catalogue operations (create/update/delete) succeed without a real dispatcher
  - Application dispatch requests are ACKed but never forwarded
  - Domibus messaging is entirely bypassed
  - Dataset metadata is managed directly via hub-repo API
  - Application status is managed directly via hdeu-access API

Usage:
    python3 stub_dispatcher.py [PORT]       # PORT defaults to 5100

Docker:
    docker compose up -d --build
"""

import json
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [stub-dispatcher] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stub-dispatcher")


class StubDispatcherHandler(BaseHTTPRequestHandler):
    """Always returns success status codes, silently drops the request body."""

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

    def _read_body(self) -> None:
        """Consume the request body so the connection is clean."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            self.rfile.read(content_length)

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger with a consistent prefix."""
        log.info("%s %s", self.client_address[0], format % args)

    # ── HTTP method handlers ────────────────────────────────────────────

    def do_GET(self):
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
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PUT(self):
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5100
    log.info("Stub dispatcher listening on port %d", port)
    HTTPServer(("0.0.0.0", port), StubDispatcherHandler).serve_forever()
