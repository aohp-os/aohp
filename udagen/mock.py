from __future__ import annotations

import json
from textwrap import dedent
from typing import Any

from .models import InputBundle
from .utils import slugify


def create_mock_file_map(bundle: InputBundle, runtime_fixtures: dict[str, Any] | None = None) -> dict[str, str]:
    runtime_fixtures = runtime_fixtures or {}
    fixtures: dict[str, Any] = {}
    routes: list[dict[str, Any]] = []

    for source in bundle.files:
        preview = source.parsed_preview
        interface_routes = _routes_from_interface_examples(source, runtime_fixtures)
        if interface_routes is not None:
            for route, fixture_id, fixture_payload in interface_routes:
                fixtures[fixture_id] = fixture_payload
                routes.append(route)
            continue

        if source.kind == "openapi" and isinstance(preview, dict):
            for endpoint in preview.get("endpoints", []):
                route_id = slugify(f"{endpoint.get('method', 'GET')}-{endpoint.get('path', '/')}", "route")
                response = _runtime_fixture_for_endpoint(endpoint, route_id, runtime_fixtures)
                if response is None:
                    response = _sample_from_schema(endpoint.get("response_schema"), route_id)
                fixtures[route_id] = response
                routes.append(
                    {
                        "id": route_id,
                        "method": (endpoint.get("method") or "GET").upper(),
                        "path": endpoint.get("path") or "/",
                        "source": source.path,
                        "operation_id": endpoint.get("operation_id") or "",
                        "summary": endpoint.get("summary") or "",
                        "status": 200,
                        "fixture": route_id,
                    }
                )
        elif source.kind == "json_schema" and isinstance(preview, dict):
            fixture_id = slugify(preview.get("title") or source.path, "schema-fixture")
            fixtures[fixture_id] = _sample_from_schema(preview, fixture_id)
        elif source.kind in {"json_sample", "tabular_sample"} and preview is not None:
            fixture_id = slugify(source.path, "sample-fixture")
            fixtures[fixture_id] = preview

    for fixture_id, fixture_data in runtime_fixtures.items():
        fixtures.setdefault(slugify(fixture_id, "runtime-fixture"), fixture_data)

    if not routes:
        routes.append(
            {
                "id": "health",
                "method": "GET",
                "path": "/health",
                "source": "generated",
                "operation_id": "health",
                "summary": "Health check endpoint",
                "status": 200,
                "fixture": "health",
            }
        )
        fixtures.setdefault("health", {"ok": True, "service": "udagen-mock"})

    return {
        "mock/routes.json": json.dumps(routes, ensure_ascii=False, indent=2),
        "mock/fixtures.json": json.dumps(fixtures, ensure_ascii=False, indent=2),
        "mock/server.py": _server_template(),
        "mock/README.md": _readme_template(routes),
    }


def _routes_from_interface_examples(source: Any, runtime_fixtures: dict[str, Any]) -> list[tuple[dict[str, Any], str, Any]] | None:
    if source.kind != "json_sample" or not str(source.path).endswith("interface_examples.json"):
        return None
    preview = source.parsed_preview
    if not isinstance(preview, dict):
        return []
    interfaces = preview.get("interfaces")
    if not isinstance(interfaces, list):
        return []

    extracted: list[tuple[dict[str, Any], str, Any]] = []
    for item in interfaces:
        if not isinstance(item, dict):
            continue
        method = str(item.get("method") or "GET").upper()
        path = str(item.get("path") or "/")
        name = str(item.get("name") or f"{method} {path}")
        fixture_id = slugify(name or f"{method}-{path}", "interface")
        fixture_payload = _runtime_fixture_for_interface(item, fixture_id, runtime_fixtures)
        extracted.append(
            (
                {
                    "id": fixture_id,
                    "method": method,
                    "path": path,
                    "source": source.path,
                    "operation_id": name,
                    "summary": str(item.get("description") or item.get("purpose") or ""),
                    "status": int(item.get("status", 200) or 200),
                    "fixture": fixture_id,
                },
                fixture_id,
                fixture_payload,
            )
        )
    return extracted


def _runtime_fixture_for_interface(item: dict[str, Any], fixture_id: str, runtime_fixtures: dict[str, Any]) -> Any:
    for key in (fixture_id, item.get("name"), item.get("path")):
        if not key:
            continue
        normalized = slugify(str(key), "fixture")
        for runtime_key, runtime_value in runtime_fixtures.items():
            if slugify(str(runtime_key), "fixture") == normalized:
                return runtime_value
    if "response" in item:
        return item["response"]
    if "response_example" in item:
        return item["response_example"]
    return {"ok": True, "interface": item.get("name") or fixture_id}


def _runtime_fixture_for_endpoint(endpoint: dict[str, Any], route_id: str, runtime_fixtures: dict[str, Any]) -> Any | None:
    if not runtime_fixtures:
        return None

    path = str(endpoint.get("path") or "/")
    method = str(endpoint.get("method") or "GET").lower()
    operation_id = str(endpoint.get("operation_id") or "")
    path_parts = [part for part in path.split("/") if part and not part.startswith("{")]
    last_part = path_parts[-1] if path_parts else ""
    singular_last_part = last_part[:-1] if last_part.endswith("s") else last_part
    collection_part = path_parts[0] if path_parts else ""

    candidates = [
        route_id,
        operation_id,
        path.strip("/"),
        path.strip("/").replace("/", "-").replace("{", "").replace("}", ""),
        f"{method}-{last_part}",
        f"{last_part}-response",
        f"{last_part}_response",
        f"{singular_last_part}-response",
        f"{singular_last_part}_response",
        last_part,
        singular_last_part,
        collection_part,
    ]
    normalized = {
        slugify(key, "fixture"): value
        for key, value in runtime_fixtures.items()
    }
    for candidate in candidates:
        if not candidate:
            continue
        key = slugify(candidate, "fixture")
        if key in normalized:
            value = normalized[key]
            if "{" in path and isinstance(value, list):
                return value[0] if value else {}
            return value
    return None


def _sample_from_schema(schema: Any, name_hint: str = "item", depth: int = 0) -> Any:
    if depth > 6:
        return None
    if not isinstance(schema, dict):
        return {"id": f"{name_hint}-1", "name": f"Sample {name_hint}"}

    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]
    if "oneOf" in schema and isinstance(schema["oneOf"], list) and schema["oneOf"]:
        return _sample_from_schema(schema["oneOf"][0], name_hint, depth + 1)
    if "anyOf" in schema and isinstance(schema["anyOf"], list) and schema["anyOf"]:
        return _sample_from_schema(schema["anyOf"][0], name_hint, depth + 1)
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged: dict[str, Any] = {}
        for item in schema["allOf"]:
            sample = _sample_from_schema(item, name_hint, depth + 1)
            if isinstance(sample, dict):
                merged.update(sample)
        return merged

    schema_type = schema.get("type")
    if schema_type == "array":
        return [_sample_from_schema(schema.get("items"), name_hint, depth + 1)]
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if not properties:
            return {"id": f"{name_hint}-1", "name": f"Sample {name_hint}"}
        return {
            prop_name: _sample_from_schema(prop_schema, prop_name, depth + 1)
            for prop_name, prop_schema in properties.items()
        }
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return "2026-05-31"
        if fmt == "date-time":
            return "2026-05-31T09:00:00Z"
        if fmt == "email":
            return "user@example.com"
        if fmt == "uri":
            return "https://example.com"
        return f"Sample {name_hint.replace('_', ' ')}"
    return {"id": f"{name_hint}-1", "name": f"Sample {name_hint}"}


def _server_template() -> str:
    return dedent(
        r'''
        from __future__ import annotations

        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import copy
        import json
        from pathlib import Path
        import re
        from urllib.parse import urlparse

        ROOT = Path(__file__).resolve().parent
        ROUTES = json.loads((ROOT / "routes.json").read_text(encoding="utf-8"))
        FIXTURES = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))


        def match_route(template: str, path: str) -> bool:
            pattern = re.escape(template)
            pattern = re.sub(r"\\\{[^/]+\\\}", r"[^/]+", pattern)
            return re.fullmatch(pattern, path) is not None


        class MockHandler(BaseHTTPRequestHandler):
            server_version = "UDAGenMock/0.1"

            def do_OPTIONS(self):
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_PUT(self):
                self._handle("PUT")

            def do_PATCH(self):
                self._handle("PATCH")

            def do_DELETE(self):
                self._handle("DELETE")

            def _handle(self, method: str):
                parsed = urlparse(self.path)
                route = next(
                    (
                        item
                        for item in ROUTES
                        if item.get("method") == method and match_route(item.get("path", "/"), parsed.path)
                    ),
                    None,
                )
                if route is None:
                    self._json(
                        404,
                        {
                            "error": "Route not found",
                            "method": method,
                            "path": parsed.path,
                            "available": [f"{r.get('method')} {r.get('path')}" for r in ROUTES],
                        },
                    )
                    return

                fixture = copy.deepcopy(FIXTURES.get(route.get("fixture"), {"ok": True}))
                if method in {"POST", "PUT", "PATCH"}:
                    body = self._read_json_body()
                    if isinstance(fixture, dict) and isinstance(body, dict):
                        fixture.update(body)
                    elif body is not None and fixture in ({}, None):
                        fixture = body
                self._json(int(route.get("status", 200)), fixture)

            def _read_json_body(self):
                length = int(self.headers.get("content-length", "0") or 0)
                if length <= 0:
                    return None
                raw = self.rfile.read(length).decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"raw": raw}

            def _cors(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

            def _json(self, status: int, payload):
                data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(status)
                self._cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)


        if __name__ == "__main__":
            server = ThreadingHTTPServer(("127.0.0.1", 8787), MockHandler)
            print("UDAGen mock server running at http://127.0.0.1:8787")
            print("Press Ctrl+C to stop.")
            server.serve_forever()
        '''
    ).strip() + "\n"


def _readme_template(routes: list[dict[str, Any]]) -> str:
    lines = [
        "# UDAGen Mock Server",
        "",
        "Default base URL: `http://127.0.0.1:8787`",
        "",
        "Generated apps should call this server first during testing. Bundled mock data should be treated as an offline fallback.",
        "",
        "Run:",
        "",
        "```bash",
        "python mock/server.py",
        "```",
        "",
        "Routes:",
        "",
    ]
    for route in routes:
        lines.append(f"- `{route.get('method')} {route.get('path')}` -> fixture `{route.get('fixture')}`")
    lines.append("")
    return "\n".join(lines)
