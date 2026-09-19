"""Tiny JSON HTTP server primitives; deliberately dependency-free for the lab."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


Route = Callable[[str, str, dict[str, Any]], tuple[int, dict[str, Any]]]


def serve(host: str, port: int, route: Route) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _reply(self, status: int, value: dict[str, Any]) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _dispatch(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                if not isinstance(payload, dict):
                    raise ValueError("JSON payload must be an object")
                status, response = route(self.command, self.path, payload)
            except (ValueError, KeyError) as exc:
                status, response = 400, {"error": str(exc)}
            except Exception as exc:  # The harness must remain observable on service failures.
                status, response = 500, {"error": str(exc)}
            self._reply(status, response)

        do_GET = _dispatch
        do_POST = _dispatch
        do_PUT = _dispatch

    ThreadingHTTPServer((host, port), Handler).serve_forever()
