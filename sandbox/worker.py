#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small HTTP worker for running sandbox jobs out-of-process.

The Django app can still call SandboxService directly for the MVP. This worker
gives the server deployment a clean isolation point when we want to move code
execution behind an internal HTTP service.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from sandbox.service import SandboxService


class SandboxWorkerHandler(BaseHTTPRequestHandler):
    server_version = "LuminaSandboxWorker/1.0"

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        try:
            payload = self._read_json()
            if self.path == "/run-python":
                result = SandboxService.run_python(
                    student_code=payload.get("student_code", ""),
                    test_cases=payload.get("test_cases") or [],
                )
                self._send_json(result)
                return
            if self.path == "/run-sql":
                result = SandboxService.run_sql(
                    student_sql=payload.get("student_sql", ""),
                    test_cases=payload.get("test_cases") or [],
                )
                self._send_json(result)
                return
            self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format, *args):
        return

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    host = os.getenv("SANDBOX_WORKER_HOST", "0.0.0.0")
    port = int(os.getenv("SANDBOX_WORKER_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), SandboxWorkerHandler)
    print(f"Sandbox worker listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

