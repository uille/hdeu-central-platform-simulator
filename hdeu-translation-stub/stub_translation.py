#!/usr/bin/env python3
"""
Stub Translation Service - ACKs everything, simulates translation completion with a delay.

A minimal HTTP server that mimics the translation service API surface
so that hdeu-access believes the translation service is operational. All requests
are acknowledged with the correct HTTP status code. When a translation request
is received, the stub:

1. ACKs immediately with the correct HTTP status code (204 for translation-service,
   file-translation-service; 200 for /translation)
2. Simulates processing delay (configurable via CALLBACK_DELAY_SECONDS env var,
   default 2 seconds)
3. Sends the callback to hdeu-access via the callback URL specified in the request

This enables realistic timing for testing the translation callback flow,
including potential race conditions between the scheduled translation job
and the callback handler.

Usage:
    python3 stub_translation.py [PORT]       # PORT defaults to 8084

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
from urllib.error import HTTPError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [stub-translation] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stub-translation")

API_KEY = os.environ.get("STUB_API_KEY", "c0107b96-78a1-408e-b05f-a65eb3a3d0a8")
# Delay (seconds) before sending the callback after ACK
CALLBACK_DELAY_SECONDS = int(os.environ.get("CALLBACK_DELAY_SECONDS", "2"))


class StubTranslationHandler(BaseHTTPRequestHandler):
    ROUTE_STATUS = {
        "POST": {
            "/translation-service": 204,
            "/file-translation-service": 204,
            "/translation": 200,
        },
        "GET": {
            "/translation": 200,
        },
    }

    def _route_key(self) -> str:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        return path

    def _get_response_code(self) -> int:
        path = self._route_key()
        method = self.command
        for m, routes in self.ROUTE_STATUS.items():
            if m == method:
                for route, code in routes.items():
                    if path == route or path.startswith(route):
                        return code
        return 200

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                log.info("_read_body: %s", body.decode("utf-8"))
            except UnicodeDecodeError:
                log.info("_read_body: %s", repr(body))
            return body
        return b""

    def _parse_request(self) -> dict:
        body = self._read_body()
        result = {"raw_body": body, "parsed": None}
        if not body:
            return result
        try:
            data = json.loads(body)
            result["parsed"] = data
            # Support both Flow 1/2 (applicationId/applicationType) and Flow 3 (id/type) payload formats
            result["app_id"] = data.get("data", {}).get(
                "applicationId", data.get("data", {}).get("id", "unknown")
            )
            result["app_type"] = data.get("data", {}).get(
                "applicationType", data.get("data", {}).get("type", "unknown")
            )
            result["callback_url"] = data.get("callback", {}).get("url", "")
        except (json.JSONDecodeError, AttributeError) as e:
            log.warning("Failed to parse request body: %s", e)
        return result

    def _send_callback(self, callback_url: str, callback_data: dict) -> bool:
        if not callback_url:
            log.warning("No callback URL provided, skipping callback")
            return False
        try:
            callback_json = json.dumps(callback_data).encode("utf-8")
            log.info("Sending callback to %s", callback_url)
            req = urllib_request.Request(
                callback_url,
                data=callback_json,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                },
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=10) as resp:
                log.info("Callback sent to %s -> %d", callback_url, resp.status)
                return True
        except HTTPError as e:
            log.error("HTTP Error %d when sending callback to %s: %s", e.code, callback_url, e.read().decode('utf-8', errors='replace')[:300])
            return False
        except Exception as e:
            log.error("Failed to send callback to %s: %s", callback_url, e)
            return False

    def _simulate_form_callback(self, parsed: dict) -> dict:
        request_data = parsed.get("parsed", {})
        data = request_data.get("data", {})
        # Flow 3: dict is at root level; Flow 2: dict is under data
        dict_data = request_data.get("dict", data.get("dict", {}))

        # Extract id from request payload (Flow 3) or app_id (Flow 1/2)
        request_id = request_data.get("id", data.get("applicationId", str(uuid.uuid4())))

        app_id = data.get("applicationId", data.get("id", "unknown"))
        app_type = data.get("applicationType", data.get("type", "unknown"))

        mock_dict = {}
        for section_key, section_value in dict_data.items():
            mock_dict[section_key] = {}
            if isinstance(section_value, dict):
                for field_key, field_value in section_value.items():
                    if isinstance(field_value, dict):
                        # Flow 3: field value is wrapped as {value, sourceLanguage, targetLanguages}
                        original_value = field_value.get("value", "")
                        target_langs = field_value.get("targetLanguages", ["en"])
                        mock_dict[section_key][field_key] = {
                            "value": original_value,
                            "sourceLanguage": field_value.get("sourceLanguage", "LD"),
                            "targetLanguages": target_langs,
                            "translations": {lang: original_value for lang in target_langs},
                        }
                    elif isinstance(field_value, str):
                        # Flow 2: field value is a plain string
                        mock_dict[section_key][field_key] = {
                            "value": field_value,
                            "translations": {"en": field_value},
                        }
                    else:
                        # Fallback: pass through as-is
                        mock_dict[section_key][field_key] = field_value
            else:
                mock_dict[section_key] = section_value
        return {
            "id": request_id,
            "data": {
                "id": app_id,
                "type": app_type,
                "applicationId": app_id,
                "applicationType": app_type,
            },
            "dict": mock_dict,
        }

    def _simulate_file_callback(self, parsed: dict) -> dict:
        data = parsed.get("parsed", {}).get("data", {})
        app_id = data.get("applicationId", "unknown")
        app_type = data.get("applicationType", "unknown")
        # FIX: dict is at root level of request, NOT nested under data
        dict_data = parsed.get("parsed", {}).get("dict", {})
        file_section = dict_data.get("file", {})

        file_id = None
        doc_meta = {}
        for fid, fdata in file_section.items():
            file_id = fid
            doc_meta = fdata.get("documentToTranslateBase64", {})
            break

        if not file_id:
            file_id = str(uuid.uuid4())[:8]

        original_base64 = doc_meta.get("content", "")
        if not original_base64:
            original_base64 = doc_meta.get("base64Content", "")
        
        file_format = doc_meta.get("format", "application/pdf")
        file_name = doc_meta.get("fileName", "document.pdf")

        log.info("File metadata: id=%s, format=%s, fileName=%s, contentLength=%d",
                 file_id, file_format, file_name, len(original_base64))
        
        if not original_base64:
            log.warning("File content is empty, using placeholder PDF")
            original_base64 = "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPD4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA0IDAgUgo+Pgo+Pgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSA0OTM0IGYgCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjQ1IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNQovUm9vdCAxIDAgUgo+PgpzdGFydHhyZWYKMzQyCiUlRU9GCg=="

        file_dict = {
            "translations": {},
            "documentToTranslateBase64": {
                "format": file_format,
                "fileName": file_name,
            },
        }

        target_langs = data.get("targetLanguages", ["EN"])
        for lang in target_langs:
            file_dict["translations"][lang] = original_base64

        return {
            "id": app_id,
            "data": {
                "id": app_id,
                "type": app_type,
                "applicationId": app_id,
                "applicationType": app_type,
            },
            "dict": {
                "file": {
                    file_id: file_dict,
                }
            },
        }

    def log_message(self, format: str, *args) -> None:
        log.info("%s %s", self.client_address[0], format % args)

    def do_GET(self):
        log.info("do_GET with ")
        self._read_body()
        code = self._get_response_code()
        body = b'{"status": "ok"}'
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        log.info("do_POST with ")
        parsed = self._parse_request()
        code = self._get_response_code()
        path = self._route_key()

        if "/translation-service" in path:
            req_type = "form translation"
        elif "/file-translation-service" in path:
            req_type = "file translation"
        elif path == "/translation":
            req_type = "translation callback"
        else:
            req_type = "unknown"

        if req_type in ("form translation", "file translation") and parsed.get("parsed"):
            app_id = parsed.get("app_id", "unknown")
            app_type = parsed.get("app_type", "unknown")
            callback_url = parsed.get("callback_url", "")

            log.info(
                "Received %s for applicationId=%s, applicationType=%s, callback=%s",
                req_type, app_id, app_type, callback_url,
            )

            if req_type == "form translation":
                callback_data = self._simulate_form_callback(parsed)
            else:
                callback_data = self._simulate_file_callback(parsed)

            log.info(
                "Simulated %s completed for applicationId=%s, scheduling callback in %ds",
                req_type, app_id, CALLBACK_DELAY_SECONDS,
            )

            # ACK immediately (below), then dispatch callback in a background thread
            # This simulates real translation service processing time
            if callback_url:
                timer = threading.Timer(
                    CALLBACK_DELAY_SECONDS,
                    self._send_callback,
                    args=[callback_url, callback_data],
                )
                timer.daemon = True
                timer.start()
            else:
                log.warning("No callback URL in request, callback not sent")

        else:
            log.info("ACK %s -> %s (simulated %s completed)",
                     self.client_address[0], path, req_type)

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PUT(self):
        log.info("do_PUT with ")
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        log.info("do_DELETE with ")
        self._read_body()
        code = self._get_response_code()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8084
    log.info("Stub translation service listening on port %d (API_KEY=%s)", port, API_KEY)
    log.info("Callback delay: %d seconds", CALLBACK_DELAY_SECONDS)
    HTTPServer(("0.0.0.0", port), StubTranslationHandler).serve_forever()
