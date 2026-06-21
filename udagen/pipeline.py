from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
import mimetypes
from pathlib import Path
import time
from typing import Any, Callable

from .collector import collect_input_bundle
from .config import UdaGenerationConfig
from .llm import LLMClient, extract_response_text
from .mockgen import MockGenerationResult, generate_mock_bundle
from .prompts import (
    APP_GEN_SYSTEM_PROMPT,
    APP_GEN_USER_PROMPT,
    APP_REFINEMENT_PROMPT,
    DESIGN_SPEC_SYSTEM_PROMPT,
    DESIGN_SPEC_USER_PROMPT,
    PRD_SYSTEM_PROMPT,
    PRD_USER_PROMPT,
    REFERENCE_IMAGE_PROMPT,
)
from .prd import ProductRequirementsDoc, load_prd, prd_from_dict, write_prd
from .reference import generate_reference_artifacts
from .specs import design_spec_from_dict, input_sources_from_bundle, load_design_spec, write_design_spec
from .utils import build_logger, collect_files_as_dict, read_json_from_response, save_file_map, truncate_text


@dataclass
class GenerationResult:
    output_dir: Path
    log_path: Path
    chat_log_path: Path
    app_name: str
    mock_input_dir: Path | None = None
    mock_runtime_dir: Path | None = None
    prd_path: Path | None = None
    prd_markdown_path: Path | None = None
    design_spec_path: Path | None = None
    design_markdown_path: Path | None = None
    interface_brief_path: Path | None = None
    interface_examples_path: Path | None = None
    reference_prompt_path: Path | None = None
    reference_meta_path: Path | None = None
    reference_image_path: Path | None = None
    generated_files: list[str] = field(default_factory=list)
    stages_completed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "log_path": str(self.log_path),
            "chat_log_path": str(self.chat_log_path),
            "app_name": self.app_name,
            "mock_input_dir": str(self.mock_input_dir) if self.mock_input_dir else None,
            "mock_docs_dir": str(self.mock_input_dir) if self.mock_input_dir else None,
            "mock_runtime_dir": str(self.mock_runtime_dir) if self.mock_runtime_dir else None,
            "prd_path": str(self.prd_path) if self.prd_path else None,
            "prd_markdown_path": str(self.prd_markdown_path) if self.prd_markdown_path else None,
            "design_spec_path": str(self.design_spec_path) if self.design_spec_path else None,
            "design_markdown_path": str(self.design_markdown_path) if self.design_markdown_path else None,
            "interface_brief_path": str(self.interface_brief_path) if self.interface_brief_path else None,
            "interface_examples_path": str(self.interface_examples_path) if self.interface_examples_path else None,
            "reference_prompt_path": str(self.reference_prompt_path) if self.reference_prompt_path else None,
            "reference_meta_path": str(self.reference_meta_path) if self.reference_meta_path else None,
            "reference_image_path": str(self.reference_image_path) if self.reference_image_path else None,
            "generated_files": self.generated_files,
            "stages_completed": self.stages_completed,
        }


CompletionFn = Callable[..., Any]


def _append_unique(paths: list[str], additions: list[str], prefix: str | None = None) -> None:
    for path in additions:
        value = f"{prefix.rstrip('/')}/{path}" if prefix else path
        if value not in paths:
            paths.append(value)


class UdaPipeline:
    def __init__(self, config: UdaGenerationConfig, completion_fn: CompletionFn | None = None) -> None:
        self.config = config
        self.config.apply_environment()
        self.logger = build_logger(config.output_dir, log_file_name=config.log_file_name)
        self.chat_log_path = config.output_dir / config.chat_log_file_name
        self.llm = LLMClient(
            config=config,
            chat_log_path=self.chat_log_path,
            completion_fn=completion_fn,
            logger=self.logger,
        )
        self._mock_bundle_generated = False
        self._mock_bundle_result: MockGenerationResult | None = None
        self._last_effective_bundle: Any | None = None
        self._last_prd: ProductRequirementsDoc | None = None

    def _collect_base_bundle(self) -> Any:
        return collect_input_bundle(
            self.config.input_dir,
            app_name_hint=self.config.resolved_app_name,
            exclude_paths=self._exclude_generated_context_paths(),
        )

    def _has_structured_inputs(self, bundle: Any) -> bool:
        structured_kinds = {"openapi", "json_schema", "json_sample", "tabular_sample"}
        return any(item.kind in structured_kinds for item in bundle.files)

    def _collect_effective_bundle(self, use_mock_inputs: bool) -> Any:
        extra_dirs = self._mock_doc_dirs() if use_mock_inputs else None
        return collect_input_bundle(
            self.config.input_dir,
            app_name_hint=self.config.resolved_app_name,
            extra_dirs=extra_dirs,
            exclude_paths=self._exclude_generated_context_paths(),
        )

    def _mock_doc_dirs(self) -> list[Path]:
        if self.config.mock_docs_dir.exists():
            return [self.config.mock_docs_dir]
        if self.config.legacy_mock_input_dir.exists():
            return [self.config.legacy_mock_input_dir]
        return []

    def _has_existing_mock_inputs(self) -> bool:
        return any(candidate.exists() and any(path.is_file() for path in candidate.rglob("*")) for candidate in self._mock_doc_dirs())

    def _exclude_generated_context_paths(self) -> list[Path]:
        excludes: list[Path] = [
            self.config.app_output_dir,
            self.config.mock_runtime_dir,
            self.config.mock_docs_dir,
            self.config.legacy_mock_input_dir,
            self.config.reference_images_dir,
            self.config.output_dir / "prd.json",
            self.config.output_dir / "prd.md",
            self.config.output_dir / "design_spec.json",
            self.config.output_dir / "design_spec.md",
            self.config.output_dir / "input_manifest.json",
            self.config.output_dir / self.config.log_file_name,
            self.chat_log_path,
        ]
        return excludes

    def _should_generate_mock_bundle(self, base_bundle: Any) -> bool:
        return self.config.include_mock or not self._has_structured_inputs(base_bundle)

    def _merge_mock_result(self, result: GenerationResult, mock_result: MockGenerationResult | None) -> None:
        if mock_result is None:
            return
        result.mock_input_dir = mock_result.mock_input_dir
        result.mock_runtime_dir = mock_result.mock_runtime_dir
        result.interface_brief_path = mock_result.interface_brief_path
        result.interface_examples_path = mock_result.interface_examples_path
        _append_unique(result.generated_files, mock_result.generated_files)
        _append_unique(result.stages_completed, mock_result.stages_completed)

    def _ensure_mock_bundle(self, base_bundle: Any) -> MockGenerationResult | None:
        if self._mock_bundle_generated:
            return self._mock_bundle_result
        if not self.config.include_mock and self._has_existing_mock_inputs():
            self._mock_bundle_generated = True
            self._mock_bundle_result = None
            return None
        if not self._should_generate_mock_bundle(base_bundle):
            return None
        mock_result = self._generate_mock_bundle(base_bundle=base_bundle)
        return mock_result

    def _prepare_effective_bundle(self, result: GenerationResult, write_manifest: bool = False) -> Any:
        self.logger.info("Collecting input bundle from %s", self.config.input_dir)
        base_bundle = self._collect_base_bundle()
        mock_result = self._ensure_mock_bundle(base_bundle)
        bundle = self._collect_effective_bundle(use_mock_inputs=self._mock_bundle_generated)
        self._merge_mock_result(result, mock_result)
        if self._mock_bundle_generated and result.mock_input_dir is None:
            doc_dirs = self._mock_doc_dirs()
            if doc_dirs:
                result.mock_input_dir = doc_dirs[0]
            if self.config.mock_runtime_dir.exists():
                result.mock_runtime_dir = self.config.mock_runtime_dir
        self._refresh_known_artifact_paths(result)
        self._last_effective_bundle = bundle
        if write_manifest:
            manifest_path = self.config.output_dir / "input_manifest.json"
            manifest_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
            _append_unique(result.generated_files, ["input_manifest.json"])
        return bundle

    def _refresh_known_artifact_paths(self, result: GenerationResult) -> None:
        if result.interface_brief_path is None:
            candidate = self.config.mock_docs_dir / "interface_brief.md"
            if candidate.exists():
                result.interface_brief_path = candidate
        if result.interface_examples_path is None:
            candidate = self.config.mock_docs_dir / "interface_examples.json"
            if candidate.exists():
                result.interface_examples_path = candidate
        if result.reference_prompt_path is None and self.config.reference_prompt_path.exists():
            result.reference_prompt_path = self.config.reference_prompt_path
        if result.reference_meta_path is None and self.config.reference_meta_path.exists():
            result.reference_meta_path = self.config.reference_meta_path
        if result.reference_image_path is None and self.config.reference_image_path.exists():
            result.reference_image_path = self.config.reference_image_path

    def _read_optional_text(self, path: Path, max_chars: int = 12000) -> str:
        if not path.exists() or not path.is_file():
            return ""
        return truncate_text(path.read_text(encoding="utf-8"), max_chars)

    def _interface_context_text(self) -> str:
        parts: list[str] = []
        for path in [
            self.config.mock_docs_dir / "interface_brief.md",
            self.config.mock_docs_dir / "interface_examples.json",
            self.config.mock_docs_dir / "openapi.yaml",
        ]:
            text = self._read_optional_text(path)
            if not text:
                continue
            try:
                label = path.relative_to(self.config.output_dir).as_posix()
            except ValueError:
                label = path.as_posix()
            parts.append(f"## {label}\n{text}")
        return "\n\n".join(parts)

    def _generation_context(self, bundle: Any, prd_json: str, design_spec_json: str) -> dict[str, Any]:
        return {
            "idea": self.config.resolved_idea,
            "input_manifest": bundle.model_dump(mode="json") if hasattr(bundle, "model_dump") else {},
            "interface_context": self._interface_context_text(),
            "prd_json": json.loads(prd_json) if prd_json != "null" else None,
            "design_spec_json": json.loads(design_spec_json),
            "reference_prompt_path": "reference_images/reference_prompt.md"
            if self.config.reference_prompt_path.exists()
            else "",
            "reference_prompt": self._read_optional_text(self.config.reference_prompt_path),
            "reference_meta": self._read_optional_text(self.config.reference_meta_path),
            "reference_image_path": "reference_images/reference.png" if self.config.reference_image_path.exists() else "",
            "reference_image_input_mode": self.config.reference_image_input_mode,
        }

    def _reference_image_content_item(self) -> dict[str, Any] | None:
        if self.config.reference_image_input_mode != "vision":
            return None
        if not self.config.reference_image_path.exists():
            self.logger.info(
                "Reference image input mode is vision, but %s does not exist. Falling back to text context.",
                self.config.reference_image_path,
            )
            return None

        mime_type = mimetypes.guess_type(self.config.reference_image_path.name)[0] or "image/png"
        encoded = base64.b64encode(self.config.reference_image_path.read_bytes()).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded}",
            },
        }

    def _message_content_with_reference_image(self, text: str) -> str | list[dict[str, Any]]:
        image_item = self._reference_image_content_item()
        if image_item is None:
            return text
        return [
            {"type": "text", "text": text},
            image_item,
        ]

    def _render_reference_prompt(self, prd_json: str, design_spec_json: str) -> str:
        return (
            REFERENCE_IMAGE_PROMPT.replace("<<APP_NAME_HINT>>", self.config.resolved_app_name)
            .replace("<<IDEA>>", self.config.resolved_idea)
            .replace("<<INTERFACE_CONTEXT>>", self._interface_context_text())
            .replace("<<PRD_JSON>>", prd_json)
            .replace("<<DESIGN_SPEC_JSON>>", design_spec_json)
        )

    def _ensure_reference_artifacts(self, result: GenerationResult, prd_json: str, design_spec_json: str) -> None:
        reference_prompt = self._render_reference_prompt(prd_json=prd_json, design_spec_json=design_spec_json)
        reference_result = generate_reference_artifacts(
            config=self.config,
            prompt=reference_prompt,
            logger=self.logger,
        )
        result.reference_prompt_path = reference_result.prompt_path
        result.reference_meta_path = reference_result.meta_path
        result.reference_image_path = reference_result.image_path
        if result.reference_image_path is None and self.config.reference_image_path.exists():
            result.reference_image_path = self.config.reference_image_path
        additions = [
            reference_result.prompt_path.relative_to(self.config.output_dir).as_posix(),
            reference_result.meta_path.relative_to(self.config.output_dir).as_posix(),
        ]
        if reference_result.image_path:
            additions.append(reference_result.image_path.relative_to(self.config.output_dir).as_posix())
        _append_unique(result.generated_files, additions)
        _append_unique(result.stages_completed, ["reference_image_prompt"])

    def _load_prd_if_available(self) -> ProductRequirementsDoc | None:
        if self._last_prd is not None:
            return self._last_prd
        candidate = self.config.output_dir / "prd.json"
        if not candidate.exists():
            return None
        prd = load_prd(
            candidate,
            fallback_app_name=self.config.resolved_app_name,
            fallback_idea=self.config.resolved_idea,
        )
        self._last_prd = prd
        return prd

    def draft_prd(self) -> GenerationResult:
        self.config.validate()
        result = self._new_result()
        bundle = self._prepare_effective_bundle(result, write_manifest=True)

        self.logger.info("Drafting PRD")
        bundle_json = bundle.model_dump_json(indent=2)
        response = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": PRD_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        PRD_USER_PROMPT.replace("<<APP_NAME_HINT>>", self.config.resolved_app_name)
                        .replace("<<IDEA>>", self.config.resolved_idea)
                        .replace("<<INPUT_BUNDLE_JSON>>", bundle_json)
                    ),
                },
            ],
            temperature=self.config.design_temperature,
        )
        prd_data = read_json_from_response(extract_response_text(response))
        prd = prd_from_dict(
            prd_data,
            fallback_app_name=self.config.resolved_app_name,
            fallback_idea=self.config.resolved_idea,
        )
        if not prd.input_sources:
            prd.input_sources = input_sources_from_bundle(bundle.files)
        json_path, md_path = write_prd(prd, self.config.output_dir)
        result.prd_path = json_path
        result.prd_markdown_path = md_path
        self._last_prd = prd
        _append_unique(result.generated_files, [json_path.name, md_path.name])
        result.stages_completed.append("draft_prd")
        self.logger.info("PRD written to %s", json_path)
        return result

    def draft_design(self) -> GenerationResult:
        result = self.draft_prd()
        bundle = self._last_effective_bundle
        if bundle is None:
            bundle = self._prepare_effective_bundle(result, write_manifest=True)
        prd = self._load_prd_if_available()
        prd_json = prd.model_dump_json(indent=2) if prd else "null"

        self.logger.info("Drafting editable design spec")
        bundle_json = bundle.model_dump_json(indent=2)
        response = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": DESIGN_SPEC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        DESIGN_SPEC_USER_PROMPT.replace("<<APP_NAME_HINT>>", self.config.resolved_app_name)
                        .replace("<<PRD_JSON>>", prd_json)
                        .replace("<<INPUT_BUNDLE_JSON>>", bundle_json)
                    ),
                },
            ],
            temperature=self.config.design_temperature,
        )
        design_data = read_json_from_response(extract_response_text(response))
        spec = design_spec_from_dict(design_data, fallback_app_name=self.config.resolved_app_name)
        if not spec.input_sources:
            spec.input_sources = input_sources_from_bundle(bundle.files)
        json_path, md_path = write_design_spec(spec, self.config.output_dir)
        result.design_spec_path = json_path
        result.design_markdown_path = md_path
        _append_unique(result.generated_files, [json_path.name, md_path.name])
        result.stages_completed.append("draft_design")
        self.logger.info("Design spec written to %s", json_path)
        return result

    def build_app(self) -> GenerationResult:
        self.config.validate(require_spec=True)
        result = self._new_result()
        bundle = self._prepare_effective_bundle(result)
        spec = load_design_spec(self.config.resolved_spec_path, fallback_app_name=self.config.resolved_app_name)
        result.design_spec_path = self.config.resolved_spec_path
        prd = self._load_prd_if_available()
        prd_json = prd.model_dump_json(indent=2) if prd else "null"
        design_spec_json = spec.model_dump_json(indent=2)
        if prd is not None:
            result.prd_path = self.config.output_dir / "prd.json"
            md_path = self.config.output_dir / "prd.md"
            if md_path.exists():
                result.prd_markdown_path = md_path
        self._ensure_reference_artifacts(result, prd_json=prd_json, design_spec_json=design_spec_json)
        generation_context = self._generation_context(bundle, prd_json, design_spec_json)
        generation_context_json = json.dumps(generation_context, ensure_ascii=False, indent=2)

        self.logger.info("Generating app code into %s", self.config.app_output_dir)
        app_user_prompt = (
            APP_GEN_USER_PROMPT.replace("<<DESIGN_SPEC_JSON>>", design_spec_json)
            .replace("<<PRD_JSON>>", prd_json)
            .replace("<<INPUT_BUNDLE_JSON>>", bundle.model_dump_json(indent=2))
            .replace("<<GENERATION_CONTEXT_JSON>>", generation_context_json)
        )
        response = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": APP_GEN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._message_content_with_reference_image(app_user_prompt),
                },
            ],
            temperature=self.config.build_temperature,
        )
        file_map = read_json_from_response(extract_response_text(response))
        written = save_file_map(file_map, self.config.app_output_dir, self.logger)
        _append_unique(result.generated_files, written, prefix="app")
        result.stages_completed.append("build_app")

        if self.config.refinement_rounds > 0:
            _append_unique(result.generated_files, self._run_refinement(design_spec_json, generation_context_json), prefix="app")
            result.stages_completed.append("refinement")

        return result

    def _generate_mock_bundle(self, base_bundle: Any | None = None) -> MockGenerationResult:
        self.config.validate()
        if base_bundle is None:
            base_bundle = self._collect_base_bundle()
        result = generate_mock_bundle(self.config, self.llm, base_bundle, logger=self.logger)
        self._mock_bundle_generated = True
        self._mock_bundle_result = result
        return result

    def build_mock_bundle(self, base_bundle: Any | None = None) -> GenerationResult:
        result = self._new_result()
        mock_result = self._generate_mock_bundle(base_bundle=base_bundle)
        self._merge_mock_result(result, mock_result)
        return result

    def run_pipeline(self) -> GenerationResult:
        result = self.draft_design()
        if self.config.stop_after_spec:
            return result

        build_result = self.build_app()
        result.prd_path = build_result.prd_path or result.prd_path
        result.prd_markdown_path = build_result.prd_markdown_path or result.prd_markdown_path
        result.design_spec_path = build_result.design_spec_path or result.design_spec_path
        result.reference_prompt_path = build_result.reference_prompt_path or result.reference_prompt_path
        result.reference_meta_path = build_result.reference_meta_path or result.reference_meta_path
        result.reference_image_path = build_result.reference_image_path or result.reference_image_path
        result.interface_brief_path = build_result.interface_brief_path or result.interface_brief_path
        result.interface_examples_path = build_result.interface_examples_path or result.interface_examples_path
        if build_result.mock_input_dir and result.mock_input_dir is None:
            result.mock_input_dir = build_result.mock_input_dir
        if build_result.mock_runtime_dir and result.mock_runtime_dir is None:
            result.mock_runtime_dir = build_result.mock_runtime_dir
        _append_unique(result.generated_files, build_result.generated_files)
        _append_unique(result.stages_completed, build_result.stages_completed)
        return result

    def _run_refinement(self, design_spec_json: str, generation_context_json: str) -> list[str]:
        written_files: list[str] = []
        for round_index in range(self.config.refinement_rounds):
            self.logger.info("Refinement round %s/%s", round_index + 1, self.config.refinement_rounds)
            success = False
            for retry_index in range(self.config.max_retry):
                current_files = json.dumps(collect_files_as_dict(self.config.app_output_dir), ensure_ascii=False)
                response = self.llm.chat_completion(
                    messages=[
                        {"role": "system", "content": APP_GEN_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": self._message_content_with_reference_image(
                                "Generation context:\n```json\n"
                                + generation_context_json
                                + "\n```\n\nDesign spec:\n```json\n"
                                + design_spec_json
                                + "\n```\n\nGenerated app files:\n```json\n"
                                + current_files
                                + "\n```\n\n"
                                + APP_REFINEMENT_PROMPT
                            ),
                        },
                    ],
                    temperature=self.config.refinement_temperature,
                )
                try:
                    file_map = read_json_from_response(extract_response_text(response))
                except ValueError:
                    self.logger.warning("Could not parse refinement JSON on retry %s", retry_index + 1)
                    time.sleep(self.config.retry_sleep_seconds)
                    continue
                _append_unique(written_files, save_file_map(file_map, self.config.app_output_dir, self.logger))
                success = True
                break
            if not success:
                self.logger.error("Refinement round %s failed after retries.", round_index + 1)
        return written_files

    def _new_result(self) -> GenerationResult:
        return GenerationResult(
            output_dir=self.config.output_dir,
            log_path=self.config.output_dir / self.config.log_file_name,
            chat_log_path=self.chat_log_path,
            app_name=self.config.resolved_app_name,
            mock_input_dir=None,
        )


def draft_design(input_dir: str, output_dir: str, completion_fn: CompletionFn | None = None, **kwargs: Any) -> GenerationResult:
    config = UdaGenerationConfig.from_env_and_kwargs(input_dir=input_dir, output_dir=output_dir, **kwargs)
    return UdaPipeline(config, completion_fn=completion_fn).draft_design()


def draft_prd(input_dir: str, output_dir: str, completion_fn: CompletionFn | None = None, **kwargs: Any) -> GenerationResult:
    config = UdaGenerationConfig.from_env_and_kwargs(input_dir=input_dir, output_dir=output_dir, **kwargs)
    return UdaPipeline(config, completion_fn=completion_fn).draft_prd()


def build_app(input_dir: str, output_dir: str, completion_fn: CompletionFn | None = None, **kwargs: Any) -> GenerationResult:
    config = UdaGenerationConfig.from_env_and_kwargs(input_dir=input_dir, output_dir=output_dir, **kwargs)
    return UdaPipeline(config, completion_fn=completion_fn).build_app()


def build_mock_bundle(input_dir: str, output_dir: str, completion_fn: CompletionFn | None = None, **kwargs: Any) -> GenerationResult:
    config = UdaGenerationConfig.from_env_and_kwargs(input_dir=input_dir, output_dir=output_dir, **kwargs)
    return UdaPipeline(config, completion_fn=completion_fn).build_mock_bundle()


def run_pipeline(input_dir: str, output_dir: str, completion_fn: CompletionFn | None = None, **kwargs: Any) -> GenerationResult:
    config = UdaGenerationConfig.from_env_and_kwargs(input_dir=input_dir, output_dir=output_dir, **kwargs)
    return UdaPipeline(config, completion_fn=completion_fn).run_pipeline()
