from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import yaml

from .models import InputBundle, InputFileSummary
from .utils import truncate_text

SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv"}


def collect_input_bundle(
    input_dir: str | Path,
    app_name_hint: str | None = None,
    max_chars_per_file: int = 12000,
    extra_dirs: list[str | Path] | None = None,
    exclude_paths: list[str | Path] | None = None,
) -> InputBundle:
    root = Path(input_dir)
    files: list[InputFileSummary] = []
    warnings: list[str] = []
    excluded = [Path(path).resolve() for path in exclude_paths or []]

    roots: list[tuple[Path, str | None]] = [(root, None)]
    for extra_dir in extra_dirs or []:
        extra_root = Path(extra_dir)
        if extra_root.exists():
            roots.append((extra_root, extra_root.name or None))

    for current_root, prefix in roots:
        for path in sorted(current_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if prefix is None and _is_excluded(path, excluded):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                warnings.append(f"Skipped non-UTF-8 file: {path.relative_to(current_root).as_posix()}")
                continue

            parsed = _parse_structured(path, text, warnings, current_root)
            kind = _detect_kind(path, parsed)
            parsed_preview = _build_parsed_preview(kind, parsed)
            rel_path = path.relative_to(current_root).as_posix()
            if prefix:
                rel_path = f"{prefix}/{rel_path}"
            files.append(
                InputFileSummary(
                    path=rel_path,
                    kind=kind,
                    size_bytes=path.stat().st_size,
                    summary=_summarize_file(kind, text, parsed_preview),
                    content_preview=truncate_text(text, max_chars_per_file),
                    parsed_preview=parsed_preview,
                )
            )

    return InputBundle(input_dir=str(root), app_name_hint=app_name_hint, files=files, warnings=warnings)


def _is_excluded(path: Path, excluded: list[Path]) -> bool:
    resolved = path.resolve()
    for excluded_path in excluded:
        if resolved == excluded_path:
            return True
        try:
            resolved.relative_to(excluded_path)
            return True
        except ValueError:
            continue
    return False


def _parse_structured(path: Path, text: str, warnings: list[str], root: Path) -> Any | None:
    ext = path.suffix.lower()
    try:
        if ext == ".json":
            return json.loads(text)
        if ext in {".yaml", ".yml"}:
            return yaml.safe_load(text)
        if ext in {".csv", ".tsv"}:
            delimiter = "\t" if ext == ".tsv" else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            return {"headers": reader.fieldnames or [], "rows": rows[:20], "row_count": len(rows)}
    except Exception as exc:
        warnings.append(f"Could not parse {path.relative_to(root).as_posix()}: {exc}")
    return None


def _detect_kind(path: Path, parsed: Any | None) -> str:
    ext = path.suffix.lower()
    if ext == ".md":
        return "requirement_markdown"
    if ext == ".txt":
        return "text_context"
    if ext in {".csv", ".tsv"}:
        return "tabular_sample"
    if isinstance(parsed, dict):
        if "openapi" in parsed or "swagger" in parsed:
            return "openapi"
        if "$schema" in parsed or ("type" in parsed and "properties" in parsed):
            return "json_schema"
        return "json_sample"
    if isinstance(parsed, list):
        return "json_sample"
    return "other"


def _build_parsed_preview(kind: str, parsed: Any | None) -> Any | None:
    if parsed is None:
        return None
    if kind == "openapi" and isinstance(parsed, dict):
        return _summarize_openapi(parsed)
    if kind == "json_schema" and isinstance(parsed, dict):
        return _summarize_json_schema(parsed)
    if kind == "tabular_sample" and isinstance(parsed, dict):
        return parsed
    if kind == "json_sample":
        return _sample_json(parsed)
    return _sample_json(parsed)


def _summarize_openapi(doc: dict[str, Any]) -> dict[str, Any]:
    endpoints: list[dict[str, Any]] = []
    paths = doc.get("paths", {}) if isinstance(doc.get("paths"), dict) else {}
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": route,
                    "operation_id": operation.get("operationId") or "",
                    "summary": operation.get("summary") or operation.get("description") or "",
                    "request_schema": _extract_request_schema(operation, doc),
                    "response_schema": _extract_response_schema(operation, doc),
                }
            )

    info = doc.get("info", {}) if isinstance(doc.get("info"), dict) else {}
    return {
        "title": info.get("title", ""),
        "version": info.get("version", ""),
        "endpoint_count": len(endpoints),
        "endpoints": endpoints[:80],
    }


def _extract_request_schema(operation: dict[str, Any], root: dict[str, Any]) -> Any | None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None
    content = request_body.get("content")
    if not isinstance(content, dict):
        return None
    for media in ("application/json", "application/*+json"):
        schema = content.get(media, {}).get("schema") if isinstance(content.get(media), dict) else None
        if schema:
            return _resolve_schema_refs(schema, root)
    for media_value in content.values():
        if isinstance(media_value, dict) and media_value.get("schema"):
            return _resolve_schema_refs(media_value["schema"], root)
    return None


def _extract_response_schema(operation: dict[str, Any], root: dict[str, Any]) -> Any | None:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None
    for status in ("200", "201", "default"):
        response = responses.get(status)
        schema = _schema_from_response(response)
        if schema:
            return _resolve_schema_refs(schema, root)
    for response in responses.values():
        schema = _schema_from_response(response)
        if schema:
            return _resolve_schema_refs(schema, root)
    return None


def _schema_from_response(response: Any) -> Any | None:
    if not isinstance(response, dict):
        return None
    content = response.get("content")
    if not isinstance(content, dict):
        return None
    for media in ("application/json", "application/*+json"):
        schema = content.get(media, {}).get("schema") if isinstance(content.get(media), dict) else None
        if schema:
            return schema
    for media_value in content.values():
        if isinstance(media_value, dict) and media_value.get("schema"):
            return media_value["schema"]
    return None


def _resolve_schema_refs(schema: Any, root: dict[str, Any], depth: int = 0) -> Any:
    if depth > 8:
        return schema
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            resolved = root
            for part in ref[2:].split("/"):
                if not isinstance(resolved, dict):
                    return schema
                resolved = resolved.get(part)
            return _resolve_schema_refs(resolved, root, depth + 1)
        return {key: _resolve_schema_refs(value, root, depth + 1) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_resolve_schema_refs(item, root, depth + 1) for item in schema]
    return schema


def _summarize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    return {
        "title": schema.get("title") or schema.get("$id") or "",
        "type": schema.get("type", "object"),
        "required": schema.get("required", []),
        "properties": {
            name: {
                "type": value.get("type", "unknown") if isinstance(value, dict) else "unknown",
                "description": value.get("description", "") if isinstance(value, dict) else "",
            }
            for name, value in list(properties.items())[:80]
        },
    }


def _sample_json(value: Any, max_items: int = 20) -> Any:
    if isinstance(value, dict):
        return {key: _sample_json(item, max_items) for key, item in list(value.items())[:max_items]}
    if isinstance(value, list):
        return [_sample_json(item, max_items) for item in value[:max_items]]
    return value


def _summarize_file(kind: str, text: str, parsed_preview: Any | None) -> str:
    if kind == "openapi" and isinstance(parsed_preview, dict):
        title = parsed_preview.get("title") or "OpenAPI"
        count = parsed_preview.get("endpoint_count", 0)
        return f"{title} API contract with {count} endpoint(s)."
    if kind == "json_schema" and isinstance(parsed_preview, dict):
        title = parsed_preview.get("title") or "JSON Schema"
        fields = ", ".join(list((parsed_preview.get("properties") or {}).keys())[:8])
        return f"{title} schema with fields: {fields}."
    if kind == "tabular_sample" and isinstance(parsed_preview, dict):
        headers = ", ".join(parsed_preview.get("headers") or [])
        return f"Tabular sample with columns: {headers}."
    if kind in {"requirement_markdown", "text_context"}:
        first_lines = [line.strip() for line in text.splitlines() if line.strip()]
        return " ".join(first_lines[:3])[:400]
    if kind == "json_sample":
        return "JSON example data source."
    return "Input context file."
