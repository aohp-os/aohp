from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any


def _load_env_file_from_path(path: Path, override: bool = False) -> bool:
    if not path.is_file():
        return False

    loaded = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        if override or key not in os.environ:
            os.environ[key] = value
            loaded = True

    return loaded


def load_dotenv(dotenv_path: str | os.PathLike[str] | None = None, override: bool = False) -> Path | None:
    if dotenv_path is not None:
        candidate_paths = [Path(dotenv_path)]
    else:
        cwd = Path.cwd().resolve()
        candidate_paths = [cwd / ".env", *[parent / ".env" for parent in cwd.parents]]

    for path in candidate_paths:
        if _load_env_file_from_path(path, override=override):
            return path
    return None


def _to_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _optional_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None:
        return None
    raw = str(value).strip()
    return Path(raw) if raw else None


@dataclass
class UdaGenerationConfig:
    input_dir: Path
    output_dir: Path
    spec_path: Path | None = None
    app_name: str | None = None
    idea: str | None = None
    model: str = "gemini-3.1-pro-preview"
    api_key: str | None = None
    base_url: str | None = "https://api.apikey.vip/v1"
    llm_provider: str | None = "openai"
    design_temperature: float = 0.25
    build_temperature: float = 0.35
    refinement_temperature: float = 0.25
    max_tokens: int = 40960
    refinement_rounds: int = 2
    max_retry: int = 2
    retry_sleep_seconds: float = 2.0
    clear_proxy_env: bool = True
    stop_after_spec: bool = False
    include_mock: bool = False
    with_reference_image: bool = False
    skip_reference_image: bool = False
    reference_image_provider: str = "volcengine_seedream"
    reference_image_model: str = "doubao-seedream-5.0-lite"
    reference_image_size: str = "1440x2560"
    reference_image_api_key: str | None = None
    reference_image_base_url: str = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    reference_image_input_mode: str = "text"
    log_file_name: str = "udagen.log"
    chat_log_file_name: str = "udagen_chat_logs.jsonl"

    @classmethod
    def from_kwargs(cls, **kwargs: Any) -> "UdaGenerationConfig":
        input_dir = Path(kwargs.pop("input_dir"))
        output_dir = Path(kwargs.pop("output_dir"))
        spec_path = _optional_path(kwargs.pop("spec_path", None))
        idea = kwargs.pop("idea", None)
        seed_idea = kwargs.pop("seed_idea", None)
        if idea is None:
            idea = seed_idea

        for key in (
            "clear_proxy_env",
            "stop_after_spec",
            "include_mock",
            "with_reference_image",
            "skip_reference_image",
        ):
            if key in kwargs:
                kwargs[key] = _to_bool(kwargs[key], getattr(cls, key, False))
        if "reference_image_input_mode" in kwargs:
            mode = str(kwargs["reference_image_input_mode"]).strip().lower()
            if mode not in {"text", "vision"}:
                raise ValueError("reference_image_input_mode must be 'text' or 'vision'.")
            kwargs["reference_image_input_mode"] = mode

        return cls(input_dir=input_dir, output_dir=output_dir, spec_path=spec_path, idea=idea, **kwargs)

    @classmethod
    def from_env_and_kwargs(cls, **kwargs: Any) -> "UdaGenerationConfig":
        load_dotenv()
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        env_defaults: dict[str, Any] = {
            "model": os.getenv("UDA_MODEL", "gemini-3.1-pro-preview"),
            "api_key": os.getenv("UDA_API_KEY") or None,
            "base_url": os.getenv("UDA_BASE_URL", "https://api.apikey.vip/v1"),
            "llm_provider": os.getenv("UDA_LLM_PROVIDER", "openai"),
            "idea": os.getenv("UDA_IDEA") or os.getenv("UDA_SEED_IDEA") or None,
            "max_tokens": int(os.getenv("UDA_MAX_TOKENS", "40960")),
            "refinement_rounds": int(os.getenv("UDA_REFINEMENT_ROUNDS", "2")),
            "max_retry": int(os.getenv("UDA_MAX_RETRY", "2")),
            "retry_sleep_seconds": float(os.getenv("UDA_RETRY_SLEEP_SECONDS", "2")),
            "clear_proxy_env": _to_bool(os.getenv("UDA_CLEAR_PROXY_ENV"), True),
            "with_reference_image": _to_bool(os.getenv("UDA_WITH_REFERENCE_IMAGE"), False),
            "skip_reference_image": _to_bool(os.getenv("UDA_SKIP_REFERENCE_IMAGE"), False),
            "reference_image_provider": os.getenv("UDA_REFERENCE_IMAGE_PROVIDER", "volcengine_seedream"),
            "reference_image_model": os.getenv("UDA_REFERENCE_IMAGE_MODEL", "doubao-seedream-5-0-260128"),
            "reference_image_size": os.getenv("UDA_REFERENCE_IMAGE_SIZE", "1440x2560"),
            "reference_image_api_key": os.getenv("UDA_REFERENCE_IMAGE_API_KEY") or os.getenv("ARK_API_KEY") or None,
            "reference_image_base_url": os.getenv(
                "UDA_REFERENCE_IMAGE_BASE_URL",
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            ),
            "reference_image_input_mode": os.getenv("UDA_REFERENCE_IMAGE_INPUT_MODE", "text"),
        }
        merged = {**env_defaults, **kwargs}
        return cls.from_kwargs(**merged)

    @property
    def resolved_app_name(self) -> str:
        if self.app_name:
            return self.app_name
        return self.input_dir.name or "User Defined App"

    @property
    def resolved_idea(self) -> str:
        if self.idea:
            return self.idea
        if self.app_name:
            return self.app_name
        return self.input_dir.name or "User Defined App"

    @property
    def resolved_spec_path(self) -> Path:
        return self.spec_path or (self.output_dir / "design_spec.json")

    @property
    def app_output_dir(self) -> Path:
        return self.output_dir / "app"

    @property
    def mock_input_dir(self) -> Path:
        return self.mock_docs_dir

    @property
    def mock_docs_dir(self) -> Path:
        return self.output_dir / "mock_docs"

    @property
    def legacy_mock_input_dir(self) -> Path:
        return self.output_dir / "mock_inputs"

    @property
    def mock_runtime_dir(self) -> Path:
        return self.output_dir / "mock"

    @property
    def reference_images_dir(self) -> Path:
        return self.output_dir / "reference_images"

    @property
    def reference_prompt_path(self) -> Path:
        return self.reference_images_dir / "reference_prompt.md"

    @property
    def reference_meta_path(self) -> Path:
        return self.reference_images_dir / "reference_meta.json"

    @property
    def reference_image_path(self) -> Path:
        return self.reference_images_dir / "reference.png"

    def apply_environment(self) -> None:
        if self.clear_proxy_env:
            for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
                os.environ.pop(key, None)

    def validate(self, require_spec: bool = False) -> None:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")
        if require_spec and not self.resolved_spec_path.exists():
            raise FileNotFoundError(
                f"Design spec does not exist: {self.resolved_spec_path}. Run `python -m udagen draft` first."
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)
