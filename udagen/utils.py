from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Iterable


DEFAULT_GENERATED_EXTENSIONS = {".html", ".css", ".js", ".json", ".md", ".py"}
DEFAULT_EXCLUDE_EXTENSIONS = {".log", ".jsonl"}


def truncate_text(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2 :]
    return f"{head}\n\n...[truncated {len(text) - max_chars} chars]...\n\n{tail}"


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def extract_json_from_response(response_text: str | None) -> str | None:
    if not response_text:
        return None

    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()

    try:
        json.loads(response_text)
        return response_text.strip()
    except Exception:
        pass

    first_brace = response_text.find("{")
    last_brace = response_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = response_text[first_brace : last_brace + 1]
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            return None

    return None


def read_json_from_response(response_text: str | None) -> dict[str, Any]:
    extracted = extract_json_from_response(response_text)
    if not extracted:
        raise ValueError("LLM response did not contain a valid JSON object.")
    parsed = json.loads(extracted)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def safe_write_text(root: Path, relative_path: str, content: str) -> Path:
    if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        raise ValueError(f"Unsafe output path: {relative_path}")

    root_resolved = root.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"Unsafe output path: {relative_path}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def save_file_map(files_data: dict[str, Any], output_folder: str | os.PathLike[str], logger: logging.Logger | None = None) -> list[str]:
    output_root = Path(output_folder)
    output_root.mkdir(parents=True, exist_ok=True)
    output_root_resolved = output_root.resolve()

    written_paths: list[str] = []
    for filename, content in files_data.items():
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        file_path = safe_write_text(output_root, filename, content)
        written_paths.append(file_path.relative_to(output_root_resolved).as_posix())
        if logger:
            logger.info("Saved: %s", filename)
    return written_paths


def should_include_generated_file(
    file_name: str,
    include_extensions: Iterable[str] = DEFAULT_GENERATED_EXTENSIONS,
    exclude_extensions: Iterable[str] = DEFAULT_EXCLUDE_EXTENSIONS,
) -> bool:
    ext = os.path.splitext(file_name)[1]
    return ext in set(include_extensions) and ext not in set(exclude_extensions)


def collect_files_as_dict(
    root_dir: str | os.PathLike[str],
    include_extensions: Iterable[str] = DEFAULT_GENERATED_EXTENSIONS,
    exclude_extensions: Iterable[str] = DEFAULT_EXCLUDE_EXTENSIONS,
) -> dict[str, str]:
    root = Path(root_dir)
    files_dict: dict[str, str] = {}

    if not root.exists():
        return files_dict

    for current_root, _, files in os.walk(root):
        for file_name in sorted(files):
            if not should_include_generated_file(file_name, include_extensions, exclude_extensions):
                continue
            abs_path = Path(current_root) / file_name
            rel_path = abs_path.relative_to(root).as_posix()
            try:
                files_dict[rel_path] = abs_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
    return files_dict


def build_logger(
    output_dir: str | os.PathLike[str],
    logger_name: str = "udagen",
    log_file_name: str = "udagen.log",
) -> logging.Logger:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(output_path / log_file_name, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
