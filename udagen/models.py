from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class InputFileSummary(FlexibleModel):
    path: str
    kind: str
    size_bytes: int
    summary: str
    content_preview: str = ""
    parsed_preview: Any | None = None


class InputBundle(FlexibleModel):
    input_dir: str
    app_name_hint: str | None = None
    files: list[InputFileSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceReference(FlexibleModel):
    path: str
    kind: str
    summary: str = ""


class DomainEntity(FlexibleModel):
    name: str
    description: str = ""
    fields: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)


class ApiBinding(FlexibleModel):
    name: str
    method: str = "GET"
    path: str = ""
    purpose: str = ""
    request_shape: Any | None = None
    response_shape: Any | None = None
    source_files: list[str] = Field(default_factory=list)
    mockable: bool = True


class PageStates(FlexibleModel):
    loading: str = ""
    empty: str = ""
    error: str = ""


class PageDesign(FlexibleModel):
    id: str
    title: str
    purpose: str = ""
    route: str = ""
    layout: str = ""
    primary_components: list[str] = Field(default_factory=list)
    data_bindings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    personalization_notes: str = ""
    variant_rules: list[str] = Field(default_factory=list)
    states: PageStates = Field(default_factory=PageStates)
    responsive_notes: str = ""
    user_edit_notes: str = ""


class NavigationSpec(FlexibleModel):
    entry_page: str = "home"
    pattern: str = "bottom-tabs"
    items: list[str] = Field(default_factory=list)
    global_actions: list[str] = Field(default_factory=list)


class MockStrategy(FlexibleModel):
    mode: Literal["static", "server", "hybrid", "none"] = "hybrid"
    server_url: str = "http://127.0.0.1:8787"
    startup_command: str = "python mock/server.py"
    fixtures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DesignSpec(FlexibleModel):
    version: str = "uda-design-spec/v1"
    app_name: str
    language: str = "en"
    summary: str = ""
    primary_users: list[str] = Field(default_factory=list)
    primary_scenarios: list[str] = Field(default_factory=list)
    persona_signals: list[str] = Field(default_factory=list)
    context_signals: list[str] = Field(default_factory=list)
    link_assumptions: list[str] = Field(default_factory=list)
    variant_rules: list[str] = Field(default_factory=list)
    editable_surfaces: list[str] = Field(default_factory=list)
    input_sources: list[SourceReference] = Field(default_factory=list)
    domain_entities: list[DomainEntity] = Field(default_factory=list)
    api_plan: list[ApiBinding] = Field(default_factory=list)
    pages: list[PageDesign] = Field(default_factory=list)
    navigation: NavigationSpec = Field(default_factory=NavigationSpec)
    mock_strategy: MockStrategy = Field(default_factory=MockStrategy)
    implementation_notes: list[str] = Field(default_factory=list)
    responsive_targets: list[str] = Field(
        default_factory=lambda: ["mobile-portrait", "mobile-landscape", "desktop"]
    )
