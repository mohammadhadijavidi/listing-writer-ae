"""JSON API + bilingual (Arabic RTL / English) web UI, on the Python standard library.

Endpoints
  GET  /                    web UI
  GET  /api/health          provider info
  GET  /api/samples         list of bundled SAMPLE properties (synthetic)
  GET  /api/samples/<name>  one sample (JSON)
  GET  /api/sources         official sources behind the compliance checks
  POST /api/generate        property JSON -> listing + findings
  POST /api/check           {"text": "...", "property": {...optional}} -> findings
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from .checks import check_text, summarise
from .generate import write_listing
from .providers import ProviderError, get_provider
from .schema import Property, PropertyError
from .sources import CHECKED, SOURCES

MAX_BODY = 512 * 1024
_FONT_OK = set("abcdefghijklmnopqrstuvwxyz0123456789-.")


def _pkg(*parts: str):
    return resources.files("listing_writer_ae").joinpath(*parts)


def list_samples() -> list[str]:
    return sorted(p.name for p in _pkg("samples").iterdir() if p.name.endswith(".json"))


def load_sample(name: str) -> dict:
    if name not in list_samples():
        raise FileNotFoundError(name)
    return json.loads(_pkg("samples", name).read_text(encoding="utf-8"))


def make_handler(provider):
    class Handler(BaseHTTPRequestHandler):
        server_version = "listing-writer-ae"

        def log_message(self, fmt, *args):  # quieter default logging
            if os.getenv("LISTING_LOG"):
                super().log_message(fmt, *args)

        def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if cache:
                self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("request too large")
            raw = self.rfile.read(n) if n else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValueError("body must be JSON") from e
            if not isinstance(data, dict):
                raise ValueError("body must be a JSON object")
            return data

        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._send(200, _pkg("static", "index.html").read_bytes(), "text/html; charset=utf-8")
            if path.startswith("/fonts/"):
                name = path[len("/fonts/") :]
                if not name or set(name) - _FONT_OK or ".." in name:
                    return self._json(404, {"error": "not found"})
                f = _pkg("static", "fonts", name)
                if not f.is_file():
                    return self._json(404, {"error": "not found"})
                return self._send(200, f.read_bytes(), "font/woff2", cache=True)
            if path == "/api/health":
                return self._json(200, {"ok": True, "provider": provider.name, "model": provider.model, "mock": provider.is_mock})
            if path == "/api/samples":
                return self._json(200, {"samples": list_samples()})
            if path.startswith("/api/samples/"):
                try:
                    return self._json(200, load_sample(path.rsplit("/", 1)[1]))
                except FileNotFoundError:
                    return self._json(404, {"error": "no such sample"})
            if path == "/api/sources":
                return self._json(200, {"checked": CHECKED, "sources": SOURCES})
            return self._json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            try:
                data = self._body()
                if path == "/api/generate":
                    prop = Property.from_dict(data.get("property", data))
                    listing = write_listing(prop, provider)
                    return self._json(200, listing.to_dict())
                if path == "/api/check":
                    text = data.get("text")
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("send 'text'")
                    prop = Property.from_dict(data["property"]) if data.get("property") else None
                    findings = check_text(text, prop, require_footer=bool(data.get("require_footer", prop is not None)))
                    return self._json(200, {"findings": [f.to_dict() for f in findings], "summary": summarise(findings)})
            except (ValueError, PropertyError, TypeError) as e:
                return self._json(400, {"error": str(e)})
            except ProviderError as e:
                return self._json(502, {"error": str(e)})
            return self._json(404, {"error": "not found"})

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8000, provider_name: str | None = None, model: str | None = None) -> None:
    provider = get_provider(provider_name, model)
    httpd = ThreadingHTTPServer((host, port), make_handler(provider))
    print(f"listing-writer-ae on http://{host}:{port}  (provider: {provider.name}, model: {provider.model})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
