#!/usr/bin/env python3
"""
Stub Translation Service - ACKs everything, simulates instant translation completion.
"""

import json
import logging
import os
import sys
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
            return self.rfile.read(content_length)
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
        data = parsed.get("parsed", {}).get("data", {})
        app_id = data.get("applicationId", "unknown")
        app_type = data.get("applicationType", "unknown")
        dict_data = data.get("dict", {})
        mock_dict = {}
        for section_key, section_value in dict_data.items():
            mock_dict[section_key] = {}
            if isinstance(section_value, dict):
                for field_key, field_value in section_value.items():
                    # Flow 3: field value is wrapped as {value, sourceLanguage, targetLanguages}
                    if isinstance(field_value, dict):
                        mock_dict[section_key][field_key] = field_value.get(
                            "value", field_value
                        )
                    # Flow 2: field value is a plain string
                    elif isinstance(field_value, str):
                        mock_dict[section_key][field_key] = field_value
                    # Flow 1 fallback: pass through as-is
                    else:
                        mock_dict[section_key][field_key] = field_value
            else:
                mock_dict[section_key] = section_value
        return {
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
        log.info("do_GET")
        self._read_body()
        code = self._get_response_code()
        body = b'{"status": "ok"}'
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        log.info("do_POST")
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
                "Simulated %s completed for applicationId=%s, sending callback",
                req_type, app_id,
            )

            if callback_url:
                self._send_callback(callback_url, callback_data)
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8084
    log.info("Stub translation service listening on port %d (API_KEY=%s)", port, API_KEY)
    HTTPServer(("0.0.0.0", port), StubTranslationHandler).serve_forever()
