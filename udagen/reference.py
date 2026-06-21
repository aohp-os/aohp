from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from pathlib import Path
from typing import Any, Callable
from urllib import request

from .config import UdaGenerationConfig


ReferenceRequestFn = Callable[[dict[str, Any], UdaGenerationConfig], dict[str, Any]]


@dataclass
class ReferenceImageResult:
    prompt_path: Path
    meta_path: Path
    image_path: Path | None = None
    status: str = "skipped"


def generate_reference_artifacts(
    config: UdaGenerationConfig,
    prompt: str,
    request_fn: ReferenceRequestFn | None = None,
    logger: Any | None = None,
) -> ReferenceImageResult:
    config.reference_images_dir.mkdir(parents=True, exist_ok=True)
    config.reference_prompt_path.write_text(prompt, encoding="utf-8")

    meta: dict[str, Any] = {
        "provider": config.reference_image_provider,
        "endpoint": config.reference_image_base_url,
        "model": config.reference_image_model,
        "size": config.reference_image_size,
        "response_format": "b64_json",
        "watermark": False,
        "source_prompt_path": "reference_images/reference_prompt.md",
        "output_path": "reference_images/reference.png",
    }

    if config.skip_reference_image:
        meta["status"] = "skipped_by_flag"
        return _write_meta(config, meta, image_path=None)
    if not config.with_reference_image:
        meta["status"] = "skipped_not_requested"
        return _write_meta(config, meta, image_path=None)
    if not config.reference_image_api_key:
        meta["status"] = "skipped_missing_api_key"
        return _write_meta(config, meta, image_path=None)

    payload = {
        "model": config.reference_image_model,
        "prompt": prompt,
        "size": config.reference_image_size,
        "response_format": "b64_json",
        "watermark": False,
        "sequential_image_generation": "disabled",
    }
    try:
        response_data = request_fn(payload, config) if request_fn else _request_volcengine(payload, config)
        b64_value = _extract_b64_json(response_data)
        if not b64_value:
            meta["status"] = "failed_invalid_response"
            meta["response_preview"] = str(response_data)[:500]
            return _write_meta(config, meta, image_path=None)
        config.reference_image_path.write_bytes(base64.b64decode(b64_value))
        meta["status"] = "generated"
        return _write_meta(config, meta, image_path=config.reference_image_path)
    except Exception as exc:
        meta["status"] = "failed"
        meta["error"] = str(exc)[:500]
        if logger:
            logger.exception("Reference image generation failed: %s", exc)
        return _write_meta(config, meta, image_path=None)


def _request_volcengine(payload: dict[str, Any], config: UdaGenerationConfig) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        config.reference_image_base_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.reference_image_api_key}",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_b64_json(response_data: dict[str, Any]) -> str | None:
    data = response_data.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("b64_json"), str):
                return item["b64_json"]
    return None


def _write_meta(config: UdaGenerationConfig, meta: dict[str, Any], image_path: Path | None) -> ReferenceImageResult:
    config.reference_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return ReferenceImageResult(
        prompt_path=config.reference_prompt_path,
        meta_path=config.reference_meta_path,
        image_path=image_path,
        status=str(meta.get("status") or "skipped"),
    )
