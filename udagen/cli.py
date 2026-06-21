from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .pipeline import build_app, build_mock_bundle, draft_design, draft_prd, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UDAGen generic app generator")
    subparsers = parser.add_subparsers(dest="command")

    prd_parser = subparsers.add_parser("prd", help="Generate editable prd.json and prd.md")
    _add_common_args(prd_parser)

    draft_parser = subparsers.add_parser("draft", help="Generate PRD plus editable design_spec.json and design_spec.md")
    _add_common_args(draft_parser)

    build_parser_ = subparsers.add_parser("build", help="Generate app code from an edited design spec")
    _add_common_args(build_parser_)
    build_parser_.add_argument("--spec-path", dest="spec_path", help="Path to design_spec.json or design_spec.md")

    run_parser = subparsers.add_parser("run", help="Run draft and build in one command")
    _add_common_args(run_parser)
    run_parser.add_argument("--spec-path", dest="spec_path", help="Optional existing spec path to use for build")
    run_parser.add_argument("--stop-after-spec", action="store_true", help="Only draft the design spec")

    mock_parser = subparsers.add_parser("mock", help="Generate LLM-authored mock docs and a local mock runtime")
    _add_common_args(mock_parser, include_llm=True)

    parser.add_argument("--version", action="version", version="udagen 0.1.0")
    return parser


def _add_common_args(parser: argparse.ArgumentParser, include_llm: bool = True) -> None:
    parser.add_argument("--input-dir", "-i", required=True, help="Input directory containing requirements/API/data files")
    parser.add_argument("--output-dir", "-o", required=True, help="Output directory")
    parser.add_argument("--app-name", dest="app_name", help="App name hint")
    parser.add_argument("--idea", "--seed-idea", dest="idea", help="Seed idea used to generate mock docs and guide drafting")
    parser.add_argument("--log-json", action="store_true", help="Print JSON summary after completion")

    if include_llm:
        parser.add_argument(
            "--with-mock",
            dest="include_mock",
            action="store_true",
            help="Force generation of mock docs and runtime files",
        )
        parser.add_argument(
            "--with-reference-image",
            dest="with_reference_image",
            action="store_true",
            help="Generate reference.png when image API credentials are available",
        )
        parser.add_argument(
            "--skip-reference-image",
            dest="skip_reference_image",
            action="store_true",
            help="Skip reference image generation while keeping other context",
        )
        parser.add_argument("--reference-image-provider", dest="reference_image_provider", help="Reference image provider")
        parser.add_argument("--reference-image-model", dest="reference_image_model", help="Reference image model")
        parser.add_argument(
            "--reference-image-size",
            dest="reference_image_size",
            help="Reference image size, default 1440x2560",
        )
        parser.add_argument("--reference-image-api-key", dest="reference_image_api_key", help="Reference image API key")
        parser.add_argument(
            "--reference-image-base-url",
            dest="reference_image_base_url",
            help="Reference image API endpoint",
        )
        parser.add_argument(
            "--reference-image-input-mode",
            dest="reference_image_input_mode",
            choices=("text", "vision"),
            help="How app generation consumes the reference image: text prompt only or multimodal vision input",
        )
        parser.add_argument("--model",dest="model", help="LLM model")
        parser.add_argument("--api-key", dest="api_key", help="LLM API key")
        parser.add_argument("--base-url", dest="base_url", help="LLM base URL")
        parser.add_argument("--provider", dest="llm_provider", help="LLM provider")
        parser.add_argument("--max-tokens", dest="max_tokens", type=int, help="Max completion tokens")
        parser.add_argument("--design-temperature", dest="design_temperature", type=float, help="Design spec temperature")
        parser.add_argument("--build-temperature", dest="build_temperature", type=float, help="App generation temperature")
        parser.add_argument(
            "--refinement-temperature",
            dest="refinement_temperature",
            type=float,
            help="Refinement temperature",
        )
        parser.add_argument("--refinement-rounds", dest="refinement_rounds", type=int, help="Refinement rounds")
        parser.add_argument("--max-retry", dest="max_retry", type=int, help="Retries per refinement round")
        parser.add_argument(
            "--retry-sleep-seconds",
            dest="retry_sleep_seconds",
            type=float,
            help="Sleep between refinement retries",
        )
        parser.add_argument("--no-clear-proxy-env", dest="clear_proxy_env", action="store_false")
        parser.set_defaults(clear_proxy_env=True)


def _normalize_argv(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return argv
    if argv[0] in {"prd", "draft", "build", "run", "mock", "-h", "--help", "--version"}:
        return argv
    if any(flag in argv for flag in ("-i", "--input-dir", "-o", "--output-dir")):
        return ["run", *argv]
    return argv


def _result_to_console(result: Any, log_json: bool) -> None:
    if log_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return
    print(f"Done. Output written to: {result.output_dir}")
    if result.prd_path:
        print(f"PRD: {result.prd_path}")
    if result.prd_markdown_path:
        print(f"PRD markdown: {result.prd_markdown_path}")
    if result.design_spec_path:
        print(f"Design spec: {result.design_spec_path}")
    if result.design_markdown_path:
        print(f"Design markdown: {result.design_markdown_path}")
    if result.interface_brief_path:
        print(f"Interface brief: {result.interface_brief_path}")
    if result.interface_examples_path:
        print(f"Interface examples: {result.interface_examples_path}")
    if result.reference_prompt_path:
        print(f"Reference prompt: {result.reference_prompt_path}")
    if result.reference_meta_path:
        print(f"Reference metadata: {result.reference_meta_path}")
    if result.reference_image_path:
        print(f"Reference image: {result.reference_image_path}")
    if result.mock_input_dir:
        print(f"Mock docs: {result.mock_input_dir}")
    if result.mock_runtime_dir:
        print(f"Mock runtime: {result.mock_runtime_dir}")
    print(f"Log: {result.log_path}")
    print(f"Chat log: {result.chat_log_path}")
    if result.generated_files:
        print("Generated files:")
        for path in result.generated_files:
            print(f"  - {path}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(argv))
    if args.command is None:
        parser.print_help()
        return 0

    payload = vars(args).copy()
    command = payload.pop("command")
    log_json = payload.pop("log_json", False)

    if command == "prd":
        result = draft_prd(**payload)
    elif command == "draft":
        result = draft_design(**payload)
    elif command == "build":
        result = build_app(**payload)
    elif command == "run":
        result = run_pipeline(**payload)
    elif command == "mock":
        result = build_mock_bundle(**payload)
    else:
        parser.print_help()
        return 1

    _result_to_console(result, log_json)
    return 0
