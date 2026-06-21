from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field

from .models import FlexibleModel, SourceReference
from .utils import extract_json_from_response


class ProductRequirementsDoc(FlexibleModel):
    version: str = "uda-prd/v1"
    app_name: str
    language: str = "en"
    idea: str = ""
    product_summary: str = ""
    target_users: list[str] = Field(default_factory=list)
    persona_signals: list[str] = Field(default_factory=list)
    context_signals: list[str] = Field(default_factory=list)
    input_sources: list[SourceReference] = Field(default_factory=list)
    inferred_entities: list[str] = Field(default_factory=list)
    api_assumptions: list[str] = Field(default_factory=list)
    data_assumptions: list[str] = Field(default_factory=list)
    link_and_action_assumptions: list[str] = Field(default_factory=list)
    variant_rules: list[str] = Field(default_factory=list)
    editable_surfaces: list[str] = Field(default_factory=list)
    primary_flows: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    mock_server_notes: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)


def prd_from_dict(data: dict[str, Any], fallback_app_name: str | None = None, fallback_idea: str | None = None) -> ProductRequirementsDoc:
    if "prd" in data and isinstance(data["prd"], dict):
        data = data["prd"]
    if fallback_app_name and not data.get("app_name"):
        data["app_name"] = fallback_app_name
    if fallback_idea and not data.get("idea"):
        data["idea"] = fallback_idea
    if not data.get("product_summary"):
        data["product_summary"] = data.get("idea") or "Generated User Defined App requirements."
    return ProductRequirementsDoc.model_validate(data)


def load_prd(path: str | Path, fallback_app_name: str | None = None, fallback_idea: str | None = None) -> ProductRequirementsDoc:
    prd_path = Path(path)
    text = prd_path.read_text(encoding="utf-8")
    if prd_path.suffix.lower() in {".md", ".markdown"}:
        extracted = extract_json_from_response(text)
        if not extracted:
            raise ValueError(f"Markdown PRD does not contain a fenced JSON object: {prd_path}")
        data = json.loads(extracted)
    else:
        data = json.loads(text)
    return prd_from_dict(data, fallback_app_name=fallback_app_name, fallback_idea=fallback_idea)


def write_prd(prd: ProductRequirementsDoc, output_dir: str | Path) -> tuple[Path, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "prd.json"
    md_path = root / "prd.md"
    json_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_prd_markdown(prd), encoding="utf-8")
    return json_path, md_path


def render_prd_markdown(prd: ProductRequirementsDoc) -> str:
    lines: list[str] = []
    lines.append(f"# {prd.app_name} PRD")
    lines.append("")
    lines.append(f"- Version: `{prd.version}`")
    lines.append(f"- UI language: `{prd.language}`")
    if prd.idea:
        lines.append(f"- Source idea: {prd.idea}")
    lines.append("")

    if prd.product_summary:
        lines.append("## Product Summary")
        lines.append("")
        lines.append(prd.product_summary)
        lines.append("")

    _append_list(lines, "Target Users", prd.target_users)
    _append_list(lines, "Persona Signals", prd.persona_signals)
    _append_list(lines, "Context Signals", prd.context_signals)
    _append_list(lines, "Inferred Entities", prd.inferred_entities)
    _append_list(lines, "API Assumptions", prd.api_assumptions)
    _append_list(lines, "Data Assumptions", prd.data_assumptions)
    _append_list(lines, "Link And Action Assumptions", prd.link_and_action_assumptions)
    _append_list(lines, "Variant Rules", prd.variant_rules)
    _append_list(lines, "Editable Surfaces", prd.editable_surfaces)
    _append_list(lines, "Primary Flows", prd.primary_flows)
    _append_list(lines, "Acceptance Criteria", prd.acceptance_criteria)
    _append_list(lines, "Mock Server Notes", prd.mock_server_notes)
    _append_list(lines, "Implementation Notes", prd.implementation_notes)

    if prd.input_sources:
        lines.append("## Input Sources")
        lines.append("")
        for source in prd.input_sources:
            summary = f": {source.summary}" if source.summary else ""
            lines.append(f"- `{source.path}` ({source.kind}){summary}")
        lines.append("")

    lines.append("## Machine-Readable PRD")
    lines.append("")
    lines.append("Edit `prd.json` when possible. This JSON block is included so the Markdown file can also be reviewed or reused.")
    lines.append("")
    lines.append("```json")
    lines.append(prd.model_dump_json(indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _append_list(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    lines.append(f"## {title}")
    lines.append("")
    for value in values:
        lines.append(f"- {value}")
    lines.append("")
