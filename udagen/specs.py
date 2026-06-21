from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import DesignSpec, SourceReference
from .utils import extract_json_from_response


def design_spec_from_dict(data: dict[str, Any], fallback_app_name: str | None = None) -> DesignSpec:
    if "design_spec" in data and isinstance(data["design_spec"], dict):
        data = data["design_spec"]
    if fallback_app_name and not data.get("app_name"):
        data["app_name"] = fallback_app_name
    if not data.get("pages"):
        data["pages"] = [
            {
                "id": "home",
                "title": "Home",
                "purpose": "Main entry page for the generated app.",
                "route": "#/",
                "layout": "dashboard",
                "personalization_notes": "Use the PRD signals to prioritize relevant content.",
            }
        ]
    return DesignSpec.model_validate(data)


def load_design_spec(path: str | Path, fallback_app_name: str | None = None) -> DesignSpec:
    spec_path = Path(path)
    text = spec_path.read_text(encoding="utf-8")
    if spec_path.suffix.lower() in {".md", ".markdown"}:
        extracted = extract_json_from_response(text)
        if not extracted:
            raise ValueError(f"Markdown design spec does not contain a fenced JSON object: {spec_path}")
        data = json.loads(extracted)
    else:
        data = json.loads(text)
    return design_spec_from_dict(data, fallback_app_name=fallback_app_name)


def write_design_spec(spec: DesignSpec, output_dir: str | Path) -> tuple[Path, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "design_spec.json"
    md_path = root / "design_spec.md"
    json_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_design_markdown(spec), encoding="utf-8")
    return json_path, md_path


def input_sources_from_bundle(bundle_files: list[Any]) -> list[SourceReference]:
    sources: list[SourceReference] = []
    for item in bundle_files:
        sources.append(SourceReference(path=item.path, kind=item.kind, summary=item.summary))
    return sources


def render_design_markdown(spec: DesignSpec) -> str:
    lines: list[str] = []
    lines.append(f"# {spec.app_name} Design Spec")
    lines.append("")
    lines.append(f"- Version: `{spec.version}`")
    lines.append(f"- UI language: `{spec.language}`")
    lines.append(f"- Responsive targets: {', '.join(spec.responsive_targets)}")
    lines.append("")

    if spec.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(spec.summary)
        lines.append("")

    if spec.primary_scenarios:
        lines.append("## Primary Scenarios")
        lines.append("")
        for scenario in spec.primary_scenarios:
            lines.append(f"- {scenario}")
        lines.append("")

    if any([spec.persona_signals, spec.context_signals, spec.link_assumptions, spec.variant_rules, spec.editable_surfaces]):
        lines.append("## Personalization And Variants")
        lines.append("")
        _append_section_list(lines, "Persona signals", spec.persona_signals)
        _append_section_list(lines, "Context signals", spec.context_signals)
        _append_section_list(lines, "Link assumptions", spec.link_assumptions)
        _append_section_list(lines, "Variant rules", spec.variant_rules)
        _append_section_list(lines, "Editable surfaces", spec.editable_surfaces)
        lines.append("")

    if spec.pages:
        lines.append("## Pages")
        lines.append("")
        for page in spec.pages:
            lines.append(f"### {page.title}")
            lines.append("")
            lines.append(f"- ID: `{page.id}`")
            lines.append(f"- Route: `{page.route or '#/' + page.id}`")
            lines.append(f"- Layout: {page.layout or 'unspecified'}")
            if page.purpose:
                lines.append(f"- Purpose: {page.purpose}")
            if page.primary_components:
                lines.append(f"- Components: {', '.join(page.primary_components)}")
            if page.data_bindings:
                lines.append(f"- Data bindings: {', '.join(page.data_bindings)}")
            if page.actions:
                lines.append(f"- Actions: {', '.join(page.actions)}")
            if page.personalization_notes:
                lines.append(f"- Personalization notes: {page.personalization_notes}")
            if page.variant_rules:
                lines.append(f"- Variant rules: {', '.join(page.variant_rules)}")
            if page.responsive_notes:
                lines.append(f"- Responsive notes: {page.responsive_notes}")
            if page.user_edit_notes:
                lines.append(f"- Editable notes: {page.user_edit_notes}")
            lines.append("")

    if spec.api_plan:
        lines.append("## API Plan")
        lines.append("")
        for api in spec.api_plan:
            method = api.method.upper() if api.method else "GET"
            path = api.path or "/"
            lines.append(f"- `{method} {path}`: {api.purpose or api.name}")
        lines.append("")

    if spec.domain_entities:
        lines.append("## Domain Model")
        lines.append("")
        for entity in spec.domain_entities:
            fields = ", ".join(entity.fields) if entity.fields else "fields not specified"
            lines.append(f"- **{entity.name}**: {entity.description} ({fields})")
        lines.append("")

    lines.append("## Mock Runtime")
    lines.append("")
    lines.append(f"- Mode: `{spec.mock_strategy.mode}`")
    if spec.mock_strategy.mode in {"server", "hybrid"}:
        lines.append(f"- Server URL: `{spec.mock_strategy.server_url}`")
        lines.append(f"- Start command: `{spec.mock_strategy.startup_command}`")
    if spec.mock_strategy.fixtures:
        lines.append(f"- Fixtures: {', '.join(spec.mock_strategy.fixtures)}")
    if spec.mock_strategy.notes:
        for note in spec.mock_strategy.notes:
            lines.append(f"- Note: {note}")
    lines.append("")

    lines.append("## Machine-Readable Spec")
    lines.append("")
    lines.append("Edit `design_spec.json` when possible. This JSON block is included so the Markdown file can also be used as `--spec-path`.")
    lines.append("")
    lines.append("```json")
    lines.append(spec.model_dump_json(indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _append_section_list(lines: list[str], label: str, values: list[str]) -> None:
    if not values:
        return
    lines.append(f"**{label}:**")
    for value in values:
        lines.append(f"- {value}")
