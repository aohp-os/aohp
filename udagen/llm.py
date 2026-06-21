from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Callable, Sequence

from .config import UdaGenerationConfig

CompletionFn = Callable[..., Any]


def extract_response_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        choices = result.get("choices")
        if choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict) and "content" in message:
                    return str(message["content"])
            return str(first)
        return str(result)

    choices = getattr(result, "choices", None)
    if choices:
        first = choices[0]
        message = getattr(first, "message", None)
        if message is not None and hasattr(message, "content"):
            return str(message.content)
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict) and "content" in message:
                return str(message["content"])
        return str(first)

    if hasattr(result, "content"):
        return str(getattr(result, "content"))
    return str(result)


def _extract_usage(result: Any) -> str | None:
    usage = getattr(result, "usage", None)
    if usage is None and isinstance(result, dict):
        usage = result.get("usage")
    if usage is None:
        return None

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
        completion_tokens = usage.get("completion_tokens", completion_tokens)
        total_tokens = usage.get("total_tokens", total_tokens)

    return f"{prompt_tokens} prompt tokens, {completion_tokens} completion tokens, {total_tokens} total tokens"


@dataclass
class LLMClient:
    config: UdaGenerationConfig
    chat_log_path: Path
    completion_fn: CompletionFn | None = None
    logger: logging.Logger | None = None

    def __post_init__(self) -> None:
        self.chat_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_completion_fn(self) -> CompletionFn:
        if self.completion_fn is not None:
            return self.completion_fn
        try:
            from litellm import completion as litellm_completion
        except Exception as exc:
            raise RuntimeError(
                "litellm is required for live generation. Install dependencies or pass completion_fn in tests."
            ) from exc
        return litellm_completion

    def chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        completion_fn = self._resolve_completion_fn()
        params: dict[str, Any] = {
            "model": model or self.config.model,
            "messages": list(messages),
            "max_completion_tokens": max_tokens or self.config.max_tokens,
            "timeout": 360,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        if self.config.base_url:
            params["base_url"] = self.config.base_url
        if self.config.llm_provider:
            params["custom_llm_provider"] = self.config.llm_provider

        result = completion_fn(**params)
        self._log_completion(params["model"], list(messages), result)
        return result

    def _log_completion(self, model: str, messages: list[dict[str, Any]], result: Any) -> None:
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "model": model,
                "messages": messages,
                "response_raw": extract_response_text(result),
                "usage": _extract_usage(result),
            }
            with self.chat_log_path.open("a", encoding="utf-8") as lf:
                lf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            if self.logger:
                self.logger.info("Chat completion logged to %s", self.chat_log_path)
        except Exception as exc:
            if self.logger:
                self.logger.exception("Could not write chat log: %s", exc)
