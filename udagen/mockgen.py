from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .collector import collect_input_bundle
from .config import UdaGenerationConfig
from .llm import LLMClient, extract_response_text
from .mock import create_mock_file_map
from .prompts import MOCK_INPUT_SYSTEM_PROMPT, MOCK_INPUT_USER_PROMPT
from .utils import read_json_from_response, save_file_map


@dataclass
class MockGenerationResult:
    mock_input_dir: Path
    mock_runtime_dir: Path
    interface_brief_path: Path | None = None
    interface_examples_path: Path | None = None
    generated_files: list[str] = field(default_factory=list)
    stages_completed: list[str] = field(default_factory=list)


def generate_mock_bundle(
    config: UdaGenerationConfig,
    llm: LLMClient,
    base_bundle: Any,
    logger: Any | None = None,
) -> MockGenerationResult:
    bundle_json = base_bundle.model_dump_json(indent=2)
    response = llm.chat_completion(
        messages=[
            {"role": "system", "content": MOCK_INPUT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    MOCK_INPUT_USER_PROMPT.replace("<<IDEA>>", config.resolved_idea)
                    .replace("<<APP_NAME_HINT>>", config.resolved_app_name)
                    .replace("<<INPUT_BUNDLE_JSON>>", bundle_json)
                ),
            },
        ],
        temperature=config.design_temperature,
    )
    docs_file_map, runtime_seed_map = _split_mock_file_map(read_json_from_response(extract_response_text(response)))
    written_mock_docs = save_file_map(docs_file_map, config.output_dir, logger)

    mock_bundle = collect_input_bundle(config.mock_input_dir, app_name_hint=config.resolved_app_name)
    runtime_fixtures = _runtime_fixtures_from_file_map(runtime_seed_map)
    runtime_file_map = create_mock_file_map(mock_bundle, runtime_fixtures=runtime_fixtures)
    runtime_file_map.update(_runtime_seed_output_file_map(runtime_seed_map))
    written_runtime = save_file_map(runtime_file_map, config.output_dir, logger)
    interface_brief = config.mock_input_dir / "interface_brief.md"
    interface_examples = config.mock_input_dir / "interface_examples.json"

    return MockGenerationResult(
        mock_input_dir=config.mock_input_dir,
        mock_runtime_dir=config.mock_runtime_dir,
        interface_brief_path=interface_brief if interface_brief.exists() else None,
        interface_examples_path=interface_examples if interface_examples.exists() else None,
        generated_files=[*written_mock_docs, *written_runtime],
        stages_completed=["mock_docs", "mock_runtime"],
    )


def _split_mock_file_map(file_map: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    docs: dict[str, Any] = {}
    runtime: dict[str, Any] = {}
    for raw_path, content in file_map.items():
        clean_path = Path(str(raw_path).strip()).as_posix().lstrip("./")
        if not clean_path:
            continue

        if clean_path.startswith("mock_docs/"):
            docs_path = clean_path[len("mock_docs/") :]
            if docs_path.startswith(("samples/", "data/", "fixtures.")):
                runtime[docs_path] = content
            else:
                docs[clean_path] = content
            continue
        if clean_path.startswith("mock_runtime/"):
            runtime[clean_path[len("mock_runtime/") :]] = content
            continue
        if clean_path.startswith("mock_inputs/"):
            legacy_path = clean_path[len("mock_inputs/") :]
            if legacy_path.startswith(("samples/", "fixtures.", "data/")):
                runtime[legacy_path] = content
            else:
                docs[f"mock_docs/{legacy_path}"] = content
            continue
        if clean_path.startswith("mock/"):
            runtime[clean_path[len("mock/") :]] = content
            continue
        if clean_path.startswith(("samples/", "fixtures.", "data/")):
            runtime[clean_path] = content
            continue
        docs[f"mock_docs/{clean_path}"] = content

    return docs, runtime


def _runtime_fixtures_from_file_map(file_map: dict[str, Any]) -> dict[str, Any]:
    fixtures: dict[str, Any] = {}
    for clean_path, content in file_map.items():
        parsed = _parse_json_content(content)
        if parsed is None:
            continue
        path = Path(clean_path)
        if path.name == "fixtures.json" and isinstance(parsed, dict):
            fixtures.update(parsed)
        else:
            if path.parts and path.parts[0] == "data" and len(path.parts) > 1:
                fixture_key = Path(*path.parts[1:]).with_suffix("").as_posix().replace("/", "-")
            else:
                fixture_key = Path(path.with_suffix("")).as_posix().replace("/", "-")
            fixtures[fixture_key] = parsed
    return fixtures


def _runtime_seed_output_file_map(file_map: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for clean_path, content in file_map.items():
        safe_path = Path(clean_path).as_posix().lstrip("./")
        if not safe_path or ".." in Path(safe_path).parts:
            continue
        parts = Path(safe_path).parts
        if safe_path.lower() == "readme.md":
            output["mock/RUNTIME_DATA.md"] = content
        elif parts and parts[0] == "data" and len(parts) > 1:
            output[f"mock/data/{Path(*parts[1:]).as_posix()}"] = content
        elif parts and parts[0] == "data":
            output["mock/data/fixtures.json"] = content
        else:
            output[f"mock/data/{safe_path}"] = content
    return output


def _parse_json_content(content: Any) -> Any | None:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    if isinstance(content, (dict, list)):
        return content
    return None
