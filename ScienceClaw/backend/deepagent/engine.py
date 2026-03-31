"""
模型工厂：根据配置构造 LLM 实例。

context window 解析优先级：
  1. ModelConfig 中用户显式设置的 context_window
  2. 根据 model_name 自动匹配已知模型的 context window
  3. 全局默认值 settings.context_window（环境变量 CONTEXT_WINDOW）
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from backend.config import settings


# ─── Monkey-patch langchain-openai to preserve reasoning_content ─────────────
# MiniMax, Kimi, and other thinking-enabled models require reasoning_content
# in assistant messages for multi-turn tool-calling flows.
# langchain-openai drops this field in both directions by default.
# See: https://github.com/langchain-ai/langchain/issues/34706
try:
    from langchain_openai.chat_models import base as _lc_oai_base

    _orig_convert_dict_to_message = _lc_oai_base._convert_dict_to_message

    def _patched_convert_dict_to_message(_dict, *args, **kwargs):
        msg = _orig_convert_dict_to_message(_dict, *args, **kwargs)
        if isinstance(msg, AIMessage) and isinstance(_dict, dict):
            rc = _dict.get("reasoning_content")
            if rc is not None and "reasoning_content" not in (msg.additional_kwargs or {}):
                msg.additional_kwargs["reasoning_content"] = rc
        return msg

    _lc_oai_base._convert_dict_to_message = _patched_convert_dict_to_message

    _orig_convert_message_to_dict = _lc_oai_base._convert_message_to_dict

    def _patched_convert_message_to_dict(message, *args, **kwargs):
        result = _orig_convert_message_to_dict(message, *args, **kwargs)
        if (
            result.get("role") == "assistant"
            and hasattr(message, "additional_kwargs")
            and isinstance(message.additional_kwargs, dict)
        ):
            rc = message.additional_kwargs.get("reasoning_content")
            if rc is not None and "reasoning_content" not in result:
                result["reasoning_content"] = rc
        return result

    _lc_oai_base._convert_message_to_dict = _patched_convert_message_to_dict

    _orig_convert_delta = _lc_oai_base._convert_delta_to_message_chunk

    def _patched_convert_delta_to_message_chunk(_dict, default_class):
        chunk = _orig_convert_delta(_dict, default_class)
        if hasattr(chunk, "additional_kwargs") and isinstance(_dict, dict):
            rc = _dict.get("reasoning_content")
            if rc is not None and "reasoning_content" not in chunk.additional_kwargs:
                chunk.additional_kwargs["reasoning_content"] = rc
        return chunk

    _lc_oai_base._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk

    logger.info("[Engine] Patched langchain-openai for reasoning_content round-trip support")
except Exception as e:
    logger.warning(f"[Engine] Failed to patch langchain-openai for reasoning_content: {e}")

def _create_gemini_model(
    model_name: str,
    api_key: str,
    max_tokens: int,
    streaming: bool,
    extra_kwargs: Dict[str, Any],
) -> BaseChatModel:
    """Create a ChatGoogleGenerativeAI instance for Gemini models."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        max_output_tokens=max_tokens,
        max_retries=3,
        timeout=120,
    )
try:
    from deepagents.middleware.filesystem import FilesystemMiddleware as _DAFilesystemMiddleware
    from langchain_core.messages import ToolMessage as _LCToolMessage
    from langgraph.types import Command as _LGCommand

    if not getattr(_DAFilesystemMiddleware, "_scienceclaw_non_tool_result_patch", False):
        _orig_fs_intercept = _DAFilesystemMiddleware._intercept_large_tool_result
        _orig_fs_aintercept = _DAFilesystemMiddleware._aintercept_large_tool_result

        def _patched_fs_intercept_large_tool_result(self, tool_result, runtime):
            if not isinstance(tool_result, (_LCToolMessage, _LGCommand)):
                logger.warning(
                    "[Engine] Passing through non-ToolMessage filesystem tool result type={}",
                    type(tool_result).__name__,
                )
                return tool_result
            return _orig_fs_intercept(self, tool_result, runtime)

        async def _patched_fs_aintercept_large_tool_result(self, tool_result, runtime):
            if not isinstance(tool_result, (_LCToolMessage, _LGCommand)):
                logger.warning(
                    "[Engine] Passing through non-ToolMessage filesystem tool result type={}",
                    type(tool_result).__name__,
                )
                return tool_result
            return await _orig_fs_aintercept(self, tool_result, runtime)

        _DAFilesystemMiddleware._intercept_large_tool_result = _patched_fs_intercept_large_tool_result
        _DAFilesystemMiddleware._aintercept_large_tool_result = _patched_fs_aintercept_large_tool_result
        _DAFilesystemMiddleware._scienceclaw_non_tool_result_patch = True
        logger.info("[Engine] Patched deepagents FilesystemMiddleware for non-ToolMessage tool results")
except Exception as e:
    logger.warning(f"[Engine] Failed to patch deepagents FilesystemMiddleware: {e}")

# model_name 子串 → context window (tokens)
# 匹配顺序：从上到下，先匹配先生效（更具体的模式放前面）
# 最后更新：2026-03
_KNOWN_CONTEXT_WINDOWS: list[tuple[str, int]] = [
    # ── DeepSeek ──
    ("deepseek-v4",             1_000_000),
    ("deepseek-chat",           131_072),
    ("deepseek-reasoner",       131_072),
    ("deepseek-v3",             131_072),
    ("deepseek-r1",             131_072),
    ("deepseek-r2",             131_072),
    ("deepseek-coder",          128_000),
    # ── OpenAI ──
    ("gpt-5.4",                 1_000_000),
    ("gpt-5.2",                 1_000_000),
    ("gpt-5",                   1_000_000),
    ("gpt-4.1",                 1_047_576),
    ("gpt-4.1-mini",            1_047_576),
    ("gpt-4.1-nano",            1_047_576),
    ("o4-mini",                 200_000),
    ("o4",                      200_000),
    ("o3-pro",                  200_000),
    ("o3-mini",                 200_000),
    ("o3",                      200_000),
    ("o1-pro",                  200_000),
    ("o1-mini",                 128_000),
    ("o1",                      200_000),
    ("gpt-4o-mini",             128_000),
    ("gpt-4o",                  128_000),
    ("gpt-4.5",                 128_000),
    ("gpt-4-turbo",             128_000),
    ("gpt-4",                   8_192),
    ("gpt-3.5-turbo",           16_385),
    # ── Anthropic ──
    ("claude-opus-4.6",         200_000),
    ("claude-sonnet-4.6",       200_000),
    ("claude-opus-4.5",         200_000),
    ("claude-sonnet-4.5",       200_000),
    ("claude-sonnet-4",         200_000),
    ("claude-opus-4",           200_000),
    ("claude-haiku-4",          200_000),
    ("claude-3.7-sonnet",       200_000),
    ("claude-3.5-sonnet",       200_000),
    ("claude-3.5-haiku",        200_000),
    ("claude-3-opus",           200_000),
    ("claude-3-sonnet",         200_000),
    ("claude-3-haiku",          200_000),
    ("claude",                  200_000),
    # ── Google ──
    ("gemini-3",                1_048_576),
    ("gemini-2.5-pro",          1_048_576),
    ("gemini-2.5-flash",        1_048_576),
    ("gemini-2.5",              1_048_576),
    ("gemini-2.0-flash",        1_048_576),
    ("gemini-2.0",              1_048_576),
    ("gemini-1.5-pro",          2_097_152),
    ("gemini-1.5-flash",        1_048_576),
    ("gemini",                  1_048_576),
    # ── Qwen (Alibaba) ──
    ("qwen3-coder",             131_072),
    ("qwen3-235b",              131_072),
    ("qwen3",                   131_072),
    ("qwq",                     131_072),
    ("qwen-max",                256_000),
    ("qwen2.5-coder",           131_072),
    ("qwen2.5",                 131_072),
    ("qwen-plus",               131_072),
    ("qwen-turbo",              131_072),
    ("qwen",                    32_768),
    # ── xAI ──
    ("grok-4",                  2_000_000),
    ("grok-3",                  131_072),
    ("grok-code",               256_000),
    ("grok-2",                  131_072),
    ("grok",                    131_072),
    # ── Mistral ──
    ("mistral-large",           128_000),
    ("mistral-medium",          128_000),
    ("mistral-small",           128_000),
    ("pixtral-large",           128_000),
    ("pixtral",                 128_000),
    ("codestral",               256_000),
    ("mistral",                 32_000),
    # ── Meta Llama ──
    ("llama-4-maverick",        1_000_000),
    ("llama-4-scout",           10_000_000),
    ("llama-4",                 1_000_000),
    ("llama-3.3",               131_072),
    ("llama-3.1",               131_072),
    ("llama-3",                 8_192),
    # ── Moonshot / Kimi ──
    ("kimi-k2.5",                 256_000),
    ("kimi-k2-0905-preview",      256_000),
    ("kimi-k2-turbo-preview",     256_000),
    ("kimi-k2-thinking-turbo",    256_000),
    ("kimi-k2-thinking",          256_000),
    ("kimi-k2-0711-preview",      128_000),
    ("kimi-k2",                   128_000),
    ("kimi",                    128_000),
    ("moonshot-v1-128k",        128_000),
    ("moonshot-v1-32k",         32_000),
    ("moonshot",                128_000),
    # ── ByteDance Doubao ──
    ("doubao-seed-code",        256_000),
    ("doubao-pro",              128_000),
    ("doubao",                  128_000),
    # ── MiniMax ──
    ("minimax-text-01",         4_000_000),
    ("minimax-m2.5",            1_000_000),
    ("minimax",                 200_000),
    # ── 01.AI (Yi) ──
    ("yi-lightning",            16_384),
    ("yi-large",                32_768),
    ("yi-medium",               16_384),
    ("yi",                      16_384),
    # ── Zhipu GLM ──
    ("glm-4.7",                 200_000),
    ("glm-4.6",                 200_000),
    ("glm-4.5",                 128_000),
    ("glm-4",                   128_000),
    ("glm-3",                   128_000),
    ("glm",                     128_000),
    # ── Baichuan ──
    ("baichuan4",               128_000),
    ("baichuan3",               128_000),
    ("baichuan",                32_000),
]




def _infer_context_window(model_name: str) -> Optional[int]:
    """Try to infer context window from model_name using the known-models table."""
    lower = model_name.lower()
    for pattern, ctx in _KNOWN_CONTEXT_WINDOWS:
        if pattern in lower:
            return ctx
    return None


def _resolve_context_window(
    model_name: str,
    explicit: Optional[int] = None,
) -> int:
    """Resolve context window with priority: explicit config > name matching > global default."""
    if explicit:
        return explicit

    inferred = _infer_context_window(model_name)
    if inferred is not None:
        logger.info(f"[Engine] Auto-detected context_window={inferred:,} for model '{model_name}'")
        return inferred

    fallback = settings.context_window
    logger.warning(
        f"[Engine] Unknown model '{model_name}', using default context_window={fallback:,}. "
        f"Set context_window in model config for accurate summarization thresholds."
    )
    return fallback


def _flatten_content(msg: BaseMessage) -> BaseMessage:
    """Ensure message content is a string.

    Many OpenAI-compatible APIs (DeepSeek, Qwen, etc.) reject array-type
    content in assistant / tool messages.  This normalises list content
    back to a plain string so the request never fails on serialisation.
    """
    content = msg.content
    if not isinstance(content, list):
        return msg
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            text = block.get("text") or block.get("content")
            if text:
                parts.append(str(text))
            elif block.get("type") == "thinking":
                continue
            else:
                parts.append(json.dumps(block, ensure_ascii=False, default=str))
        else:
            parts.append(str(block))
    return msg.copy(update={"content": "\n".join(parts) or "(empty)"})


_THINKING_MODEL_PATTERNS = ("minimax", "kimi", "moonshot")
_STREAM_OPTIONS_SUPPORTED_HOST_SUFFIXES = (
    "api.openai.com",
    ".openai.com",
    ".openai.azure.com",
)
_STREAM_OPTIONS_DISABLED_HOSTS_LOGGED: set[str] = set()


def _resolve_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url:
        return base_url
    default_base_url = getattr(settings, "model_ds_base_url", None)
    return default_base_url or None


def _supports_stream_options(base_url: Optional[str]) -> bool:
    """Only send stream_options to endpoints known to support it."""
    if not base_url:
        return True

    host = (urlparse(base_url).hostname or "").lower()
    if not host:
        return False

    if any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in _STREAM_OPTIONS_SUPPORTED_HOST_SUFFIXES):
        return True

    if host not in _STREAM_OPTIONS_DISABLED_HOSTS_LOGGED:
        logger.warning(
            "[Engine] Disabling stream_options for gateway host={} base_url={}",
            host,
            base_url,
        )
        _STREAM_OPTIONS_DISABLED_HOSTS_LOGGED.add(host)
    return False


class _SafeChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass with two compatibility layers:

    1. Content flattening — prevents ``invalid type: sequence`` errors on
       providers that only accept string content.
    2. reasoning_content injection — ensures thinking-enabled models
       (MiniMax, Kimi, etc.) receive reasoning_content in all assistant
       messages, which they require for multi-turn tool-calling flows.
    """

    @property
    def _is_thinking_model(self) -> bool:
        model_lower = (
            getattr(self, "model_name", None)
            or getattr(self, "model", "")
            or ""
        ).lower()
        return any(p in model_lower for p in _THINKING_MODEL_PATTERNS)

    def _ensure_reasoning_content(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Inject reasoning_content placeholder into AIMessages for thinking models.

        Thinking-enabled APIs (MiniMax, Kimi) reject assistant messages—especially
        those with tool_calls—that lack reasoning_content when thinking mode is on.
        """
        if not self._is_thinking_model:
            return messages
        result = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                kwargs = msg.additional_kwargs or {}
                if "reasoning_content" not in kwargs:
                    msg = msg.copy(update={"additional_kwargs": {**kwargs, "reasoning_content": ""}})
            result.append(msg)
        return result

    def _sanitize_messages(self, args: tuple, kwargs: dict) -> tuple:
        """Flatten content and ensure reasoning_content, return updated args."""
        if args:
            messages = self._ensure_reasoning_content([_flatten_content(m) for m in args[0]])
            return (messages, *args[1:]), kwargs
        if "messages" in kwargs:
            kwargs["messages"] = self._ensure_reasoning_content(
                [_flatten_content(m) for m in kwargs["messages"]]
            )
        return args, kwargs

    def _effective_base_url(self) -> Optional[str]:
        return (
            getattr(self, "openai_api_base", None)
            or getattr(self, "base_url", None)
            or None
        )

    def _prepare_stream_kwargs(self, kwargs: dict) -> dict:
        kwargs = dict(kwargs)
        if _supports_stream_options(self._effective_base_url()):
            kwargs.setdefault("stream_options", {"include_usage": True})
        else:
            kwargs.pop("stream_options", None)
        return kwargs

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any):  # type: ignore[override]
        messages = self._ensure_reasoning_content([_flatten_content(m) for m in messages])
        try:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except ValueError as e:
            if "No generations found in stream" in str(e):
                logger.warning(
                    "LLM API returned empty stream (model={}, base_url={}). "
                    "Possible causes: rate limit, timeout, content filter, or API error.",
                    getattr(self, "model_name", getattr(self, "model", "?")),
                    getattr(self, "openai_api_base", "?"),
                )
                raise ValueError(
                    "模型返回了空响应，可能原因：接口限流、超时、内容过滤或服务异常。请稍后重试或检查 API 配额与密钥。"
                ) from e
            raise

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any):  # type: ignore[override]
        messages = self._ensure_reasoning_content([_flatten_content(m) for m in messages])
        try:
            return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except ValueError as e:
            if "No generations found in stream" in str(e):
                logger.warning(
                    "LLM API returned empty stream (model={}, base_url={}). "
                    "Possible causes: rate limit, timeout, content filter, or API error. "
                    "Check API key, quota, and backend logs.",
                    getattr(self, "model_name", getattr(self, "model", "?")),
                    getattr(self, "openai_api_base", "?"),
                )
                raise ValueError(
                    "模型返回了空响应，可能原因：接口限流、超时、内容过滤或服务异常。请稍后重试或检查 API 配额与密钥。"
                ) from e
            raise

    def _stream(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        args, kwargs = self._sanitize_messages(args, kwargs)
        kwargs = self._prepare_stream_kwargs(kwargs)
        return super()._stream(*args, **kwargs)

    async def _astream(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        args, kwargs = self._sanitize_messages(args, kwargs)
        kwargs = self._prepare_stream_kwargs(kwargs)
        async for chunk in super()._astream(*args, **kwargs):
            yield chunk


def _apply_profile(model: BaseChatModel, context_window: int) -> BaseChatModel:
    """Set model profile so deepagents SummarizationMiddleware can auto-compute
    context window thresholds (trigger / keep) using fraction-based settings."""
    if hasattr(model, "profile"):
        if not model.profile or "max_input_tokens" not in model.profile:
            model.profile = {"max_input_tokens": context_window}
    return model


def get_llm_model(
    config: Optional[Dict[str, Any]] = None,
    max_tokens_override: Optional[int] = None,
    streaming: bool = True,
) -> BaseChatModel:
    """
    构建 LLM 模型实例。

    Args:
        config: ModelConfig 字典（可选），含 model_name, base_url, api_key, context_window 等。
                为 None 时使用 settings 中的默认值。
        max_tokens_override: 覆盖默认 max_tokens（来自用户任务设置）。
        streaming: 是否用于流式调用。为 True 时附带 stream_options 以获取 token 统计，
                   为 False 时不传 stream_options（某些 API 在非流式调用时不接受该参数）。
    """
    effective_max_tokens = max_tokens_override or settings.max_tokens
    effective_base_url = _resolve_base_url(config.get("base_url") if config else None)

    # stream_options 仅在流式调用时传递，非流式调用时 API 会拒绝该参数
    extra_kwargs: Dict[str, Any] = {}
    if streaming and _supports_stream_options(effective_base_url):
        extra_kwargs["stream_options"] = {"include_usage": True}

    if config:
        model_name = config.get("model_name", settings.model_ds_name)
        provider = config.get("provider", "")
        ctx_window = _resolve_context_window(
            model_name,
            explicit=config.get("context_window"),
        )

        if provider == "gemini":
            api_key = config.get("api_key") or settings.model_ds_api_key
            model = _create_gemini_model(
                model_name=model_name,
                api_key=api_key,
                max_tokens=effective_max_tokens,
                streaming=streaming,
                extra_kwargs=extra_kwargs,
            )
            return _apply_profile(model, ctx_window)

        model = _SafeChatOpenAI(
            model=model_name,
            base_url=effective_base_url,
            api_key=config.get("api_key") or settings.model_ds_api_key,
            max_tokens=effective_max_tokens,
            max_retries=3,
            request_timeout=120,
            model_kwargs=extra_kwargs,
        )
        return _apply_profile(model, ctx_window)

    ctx_window = _resolve_context_window(
        settings.model_ds_name,
        explicit=settings.context_window,
    )
    model = _SafeChatOpenAI(
        model=settings.model_ds_name,
        base_url=effective_base_url,
        api_key=settings.model_ds_api_key,
        max_tokens=effective_max_tokens,
        max_retries=3,
        request_timeout=120,
        model_kwargs=extra_kwargs,
    )
    return _apply_profile(model, ctx_window)
