import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Review Agent",
    "tags": ["obsidian", "zotero", "review", "agent", "better-bibtex"],
}

_SKIP_ITEM_TYPES = {"attachment", "note"}
_TOOL_CACHE: dict[str, Any] = {}
_REQUIRED_LOCAL_SKILLS = [
    "zotero-materials-review",
    "literature-review",
    "scientific-writing",
    "obsidian-markdown",
    "materials-obsidian",
]
_SUCCESS_VAULT_MATCH_STATUSES = {"exact", "normalized_same_path"}
_PLACEHOLDER_API_KEYS = {"scienceclaw-local", "changeme", "your-api-key", "sk-placeholder"}
_REVIEW_POLISH_MAX_TOKENS = 4000
_REVIEW_SECTION_HEADINGS = [
    "## 摘要",
    "## 关键词",
    "## 引言",
    "## 技术基础与发展脉络",
    "## 主要研究方向",
    "## 代表性工作比较与讨论",
    "## 挑战与争议",
    "## 未来趋势与机会",
    "## 结论",
    "## 参考文献",
]
_THEME_KEYWORD_MAP = {
    "生成模型驱动的设计与发现": ["生成模型", "逆向设计"],
    "大语言模型与知识组织": ["大语言模型", "知识组织"],
    "多模态建模与知识增强": ["多模态建模", "结构表征"],
    "评测基准与方法比较": ["基准评测", "方法比较"],
    "智能代理与科研工作流": ["科研工作流", "智能代理"],
    "交叉方法与应用场景": ["材料应用", "交叉方法"],
}
_THEME_OVERVIEW_MAP = {
    "生成模型驱动的设计与发现": "这一方向主要关注如何用生成式建模、搜索与逆向设计框架提出候选材料、结构或工艺方案，并把目标性质约束显式纳入设计过程。",
    "大语言模型与知识组织": "这一方向主要讨论如何将大语言模型用于文献理解、知识抽取、材料性质预测以及科研助手构建，从而降低知识整理与研究交互成本。",
    "多模态建模与知识增强": "这一方向聚焦文本、结构、图表示及其他模态信息的联合建模，目标是在更完整的证据表示下提升材料结构与性质关系建模能力。",
    "评测基准与方法比较": "这一方向更强调统一数据集、评价协议与对比口径，是把研究从“能否工作”推进到“如何公平比较”的关键基础。",
    "智能代理与科研工作流": "这一方向试图把模型能力嵌入科研流程，通过任务分解、工具调用和知识回写形成可复用的自动化研究链路。",
    "交叉方法与应用场景": "这一方向承接跨学科方法迁移与场景落地，体现出当前主题并非孤立技术，而是与具体材料任务和应用目标强相关。",
}
_THEME_COMPARISON_MAP = {
    "生成模型驱动的设计与发现": "相较于单纯的预测模型，这类工作更关注候选方案生成、搜索空间约束以及设计结果的可行性验证。",
    "大语言模型与知识组织": "相较于传统特征工程路线，这类工作更强调知识压缩、跨文献归纳和自然语言交互能力。",
    "多模态建模与知识增强": "与单一文本或单一结构表示相比，这类工作更重视异构证据融合和表示之间的信息互补。",
    "评测基准与方法比较": "与方法本身的创新相比，这类工作更在意评价协议、数据拆分和结果可复现性。",
    "智能代理与科研工作流": "与单次推理能力相比，这类工作更在意流程编排、工具协同和结果回写闭环。",
    "交叉方法与应用场景": "与基础方法论文相比，这类工作更突出具体任务适配、应用边界以及跨领域迁移成本。",
}


def _vault_result_fields(
    result: dict[str, Any],
    *,
    requested_default: str = "",
    effective_default: str = "",
    source_default: str = "",
) -> dict[str, Any]:
    requested = str(result.get("requested_vault_dir", requested_default) or "").strip()
    effective = str(result.get("effective_vault_dir", result.get("vault_dir", effective_default)) or "").strip()
    source = str(result.get("effective_vault_source", result.get("vault_source", source_default)) or "").strip()
    match_status = str(result.get("vault_match_status", "") or "").strip()
    fell_back = bool(result.get("fell_back_to_default_vault", False))
    if not match_status and fell_back:
        match_status = "fallback_other_path"

    requested_match_success = result.get("requested_vault_match_success")
    if isinstance(requested_match_success, bool):
        match_success = requested_match_success
    else:
        match_success = match_status in _SUCCESS_VAULT_MATCH_STATUSES

    return {
        "requested_vault_dir": requested,
        "effective_vault_dir": effective,
        "effective_vault_source": source,
        "fell_back_to_default_vault": fell_back,
        "vault_match_status": match_status,
        "requested_vault_match_success": match_success,
        "requested_vault_dir_normalized": str(result.get("requested_vault_dir_normalized", "") or "").strip(),
        "effective_vault_dir_normalized": str(result.get("effective_vault_dir_normalized", "") or "").strip(),
    }


def _slugify_category(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", cleaned).strip("-_").lower()


def _normalize_category(value: str, topic: str) -> str:
    explicit = str(value or "").strip()
    topic_text = str(topic or "").strip()
    if not explicit:
        return topic_text
    explicit_slug = _slugify_category(explicit)
    topic_slug = _slugify_category(topic_text)
    if explicit_slug in {"material", "materials"} and topic_slug and explicit_slug != topic_slug:
        return topic_text
    return explicit


def _load_tool(filename: str, attr_name: str):
    cache_key = f"{filename}:{attr_name}"
    cached = _TOOL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    tool_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"scienceclaw_{tool_path.stem}_module", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load tool from {tool_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_obj = getattr(module, attr_name, None)
    if tool_obj is None or not hasattr(tool_obj, "invoke"):
        raise RuntimeError(f"Tool {attr_name} is unavailable in {tool_path}")

    _TOOL_CACHE[cache_key] = tool_obj
    return tool_obj


def _load_bundle_tool():
    return _load_tool("obsidian_build_zotero_review_bundle.py", "obsidian_build_zotero_review_bundle")


def _load_import_tool():
    return _load_tool("obsidian_import_zotero_bbt_json.py", "obsidian_import_zotero_bbt_json")


def _load_writer_tool():
    return _load_tool("obsidian_write_materials_note.py", "obsidian_write_materials_note")


def _backend_root_candidates() -> list[Path]:
    return [
        Path(__file__).resolve().parent.parent / "ScienceClaw",
        Path("/app/ScienceClaw"),
        Path("/app"),
        Path.cwd() / "ScienceClaw",
        Path.cwd(),
    ]


def _resolve_backend_root() -> Path | None:
    for candidate in _backend_root_candidates():
        if (candidate / "backend").exists():
            return candidate
    return None


def _parse_model_config_json(raw_value: str) -> dict[str, Any] | None:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return None
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid model_config_json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("model_config_json must decode to a JSON object")
    return parsed


def _running_inside_docker() -> bool:
    return Path("/.dockerenv").exists()


def _has_usable_api_key(value: Any) -> bool:
    api_key = str(value or "").strip()
    return bool(api_key) and api_key.lower() not in _PLACEHOLDER_API_KEYS


def _normalize_model_base_url(base_url: str) -> str:
    raw = str(base_url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw

    host = (parsed.hostname or "").strip().lower()
    replacement_host = host
    if not _running_inside_docker() and host == "host.docker.internal":
        replacement_host = "127.0.0.1"
    elif _running_inside_docker() and host in {"127.0.0.1", "localhost"}:
        replacement_host = "host.docker.internal"

    if replacement_host == host or not replacement_host:
        return raw

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"
    port = f":{parsed.port}" if parsed.port is not None else ""
    return urlunparse(
        (
            parsed.scheme,
            f"{auth}{replacement_host}{port}",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def _normalize_model_config_for_runtime(config: dict[str, Any] | None) -> dict[str, Any] | None:
    if not config:
        return None
    normalized = dict(config)
    normalized["base_url"] = _normalize_model_base_url(str(normalized.get("base_url", "") or ""))
    return normalized


def _docker_ps_names() -> list[str]:
    if _running_inside_docker():
        return []
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _pick_container_name(names: list[str], *terms: str) -> str:
    lowered = [(name.lower(), name) for name in names]
    preferred_prefixes = ("scienceclaw-",)
    for prefix in preferred_prefixes:
        for lower_name, original_name in lowered:
            if lower_name.startswith(prefix) and all(term in lower_name for term in terms):
                return original_name
    for lower_name, original_name in lowered:
        if all(term in lower_name for term in terms):
            return original_name
    return ""


def _docker_inspect(container_name: str) -> dict[str, Any] | None:
    if not container_name:
        return None
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        payload = json.loads(result.stdout)
    except Exception:
        return None
    if isinstance(payload, list) and payload:
        return payload[0] if isinstance(payload[0], dict) else None
    return None


def _docker_env_map(inspect_payload: dict[str, Any] | None) -> dict[str, str]:
    env_list = (((inspect_payload or {}).get("Config") or {}).get("Env") or [])
    env_map: dict[str, str] = {}
    for entry in env_list:
        if not isinstance(entry, str) or "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        env_map[key] = value
    return env_map


def _discover_mongo_runtime_from_docker() -> dict[str, Any] | None:
    names = _docker_ps_names()
    if not names:
        return None

    backend_container = _pick_container_name(names, "backend")
    mongo_container = _pick_container_name(names, "mongo")
    backend_inspect = _docker_inspect(backend_container)
    mongo_inspect = _docker_inspect(mongo_container)
    backend_env = _docker_env_map(backend_inspect)

    host_port = ""
    ports = (((mongo_inspect or {}).get("NetworkSettings") or {}).get("Ports") or {})
    published_bindings = ports.get("27017/tcp") or []
    if isinstance(published_bindings, list):
        for binding in published_bindings:
            if isinstance(binding, dict) and str(binding.get("HostPort", "")).strip():
                host_port = str(binding.get("HostPort")).strip()
                break

    try:
        resolved_port = int(host_port or backend_env.get("MONGODB_PORT") or 27014)
    except Exception:
        resolved_port = 27014

    return {
        "host": "127.0.0.1" if host_port else str(backend_env.get("MONGODB_HOST") or "").strip(),
        "port": resolved_port,
        "db_name": str(backend_env.get("MONGODB_DB") or "ai_agent").strip() or "ai_agent",
        "username": str(backend_env.get("MONGODB_USER") or "").strip(),
        "password": str(backend_env.get("MONGODB_PASSWORD") or "").strip(),
        "source": "docker-runtime",
    }


def _mongo_connection_specs(settings_obj: Any) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str, str]] = set()

    def add_spec(host: Any, port: Any, username: Any, password: Any, db_name: Any, source: str) -> None:
        host_text = str(host or "").strip()
        if not host_text:
            return
        try:
            port_int = int(port or 0)
        except Exception:
            return
        db_name_text = str(db_name or "ai_agent").strip() or "ai_agent"
        username_text = str(username or "").strip()
        password_text = str(password or "").strip()
        key = (host_text.lower(), port_int, username_text, password_text, db_name_text)
        if key in seen:
            return
        seen.add(key)
        specs.append(
            {
                "host": host_text,
                "port": port_int,
                "db_name": db_name_text,
                "username": username_text,
                "password": password_text,
                "source": source,
            }
        )

    add_spec(
        getattr(settings_obj, "mongodb_host", "localhost"),
        getattr(settings_obj, "mongodb_port", 27014),
        getattr(settings_obj, "mongodb_username", ""),
        getattr(settings_obj, "mongodb_password", ""),
        getattr(settings_obj, "mongodb_db_name", "ai_agent"),
        "backend-settings",
    )

    if not _running_inside_docker():
        add_spec(
            "127.0.0.1",
            getattr(settings_obj, "mongodb_port", 27014),
            getattr(settings_obj, "mongodb_username", ""),
            getattr(settings_obj, "mongodb_password", ""),
            getattr(settings_obj, "mongodb_db_name", "ai_agent"),
            "host-loopback",
        )
        add_spec(
            "127.0.0.1",
            27014,
            getattr(settings_obj, "mongodb_username", ""),
            getattr(settings_obj, "mongodb_password", ""),
            getattr(settings_obj, "mongodb_db_name", "ai_agent"),
            "docker-default-loopback",
        )

    docker_runtime = _discover_mongo_runtime_from_docker()
    if docker_runtime:
        add_spec(
            docker_runtime.get("host"),
            docker_runtime.get("port"),
            docker_runtime.get("username"),
            docker_runtime.get("password"),
            docker_runtime.get("db_name"),
            str(docker_runtime.get("source") or "docker-runtime"),
        )

    return specs


def _resolve_runtime_llm_config(model_config: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, Any]:
    backend_root = _resolve_backend_root()
    if backend_root is not None:
        backend_root_str = str(backend_root)
        if backend_root_str not in sys.path:
            sys.path.insert(0, backend_root_str)

    settings_obj = None
    try:
        from backend.config import settings as backend_settings

        settings_obj = backend_settings
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] unable to import backend settings for tool LLM loading: %s", exc)

    config: dict[str, Any] | None = _normalize_model_config_for_runtime(dict(model_config or {}) or None)
    default_api_key = getattr(settings_obj, "model_ds_api_key", "") if settings_obj is not None else ""
    if config is None and settings_obj is not None and not _has_usable_api_key(default_api_key):
        config = _load_llm_config_from_mongo()
    return config, settings_obj


def _load_llm_model(
    model_config: dict[str, Any] | None = None,
    *,
    max_tokens_override: int | None = None,
):
    config, settings_obj = _resolve_runtime_llm_config(model_config=model_config)

    try:
        from backend.deepagent.engine import get_llm_model

        return get_llm_model(config=config, max_tokens_override=max_tokens_override, streaming=False)
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] falling back to direct tool LLM loader: %s", exc)
        return _build_direct_llm(config=config, settings_obj=settings_obj, max_tokens_override=max_tokens_override)


def _build_direct_llm(
    config: dict[str, Any] | None = None,
    settings_obj: Any = None,
    *,
    max_tokens_override: int | None = None,
):
    provider = str((config or {}).get("provider", "")).strip().lower()
    model_name = str(
        (config or {}).get("model_name")
        or getattr(settings_obj, "model_ds_name", "")
        or os.environ.get("DS_MODEL")
        or "deepseek-chat"
    ).strip()
    api_key = str(
        (config or {}).get("api_key")
        or getattr(settings_obj, "model_ds_api_key", "")
        or os.environ.get("DS_API_KEY")
        or ""
    ).strip()
    base_url = _normalize_model_base_url(
        str(
        (config or {}).get("base_url")
        or getattr(settings_obj, "model_ds_base_url", "")
        or os.environ.get("DS_URL")
        or ""
        ).strip()
    )
    max_tokens_raw = max_tokens_override or getattr(settings_obj, "max_tokens", None) or os.environ.get("MAX_TOKENS") or 100000
    try:
        max_tokens = int(max_tokens_raw)
    except Exception:
        max_tokens = 100000

    if not _has_usable_api_key(api_key):
        raise RuntimeError(
            "No usable LLM API key configured for final polish. "
            "Pass --model-config-json/--model-config-file, configure an active model in ScienceClaw, or set DS_API_KEY."
        )

    if provider == "gemini" or model_name.lower().startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            max_output_tokens=max_tokens,
            max_retries=3,
            timeout=120,
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model_name,
        "api_key": api_key,
        "max_tokens": max_tokens,
        "max_retries": 3,
        "request_timeout": 120,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _effective_llm_request_config(
    model_config: dict[str, Any] | None = None,
    *,
    max_tokens_override: int | None = None,
) -> dict[str, Any]:
    config, settings_obj = _resolve_runtime_llm_config(model_config=model_config)
    provider = str((config or {}).get("provider", "")).strip().lower()
    model_name = str(
        (config or {}).get("model_name")
        or getattr(settings_obj, "model_ds_name", "")
        or os.environ.get("DS_MODEL")
        or "deepseek-chat"
    ).strip()
    api_key = str(
        (config or {}).get("api_key")
        or getattr(settings_obj, "model_ds_api_key", "")
        or os.environ.get("DS_API_KEY")
        or ""
    ).strip()
    base_url = _normalize_model_base_url(
        str(
            (config or {}).get("base_url")
            or getattr(settings_obj, "model_ds_base_url", "")
            or os.environ.get("DS_URL")
            or ""
        ).strip()
    )
    max_tokens_raw = max_tokens_override or getattr(settings_obj, "max_tokens", None) or os.environ.get("MAX_TOKENS") or 100000
    try:
        max_tokens = int(max_tokens_raw)
    except Exception:
        max_tokens = 100000

    return {
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
        "base_url": base_url,
        "max_tokens": max_tokens,
    }


def _invoke_openai_compatible_llm_via_http(
    *,
    system_prompt: str,
    user_prompt: str,
    model_config: dict[str, Any] | None = None,
    max_tokens_override: int | None = None,
) -> str:
    request_config = _effective_llm_request_config(
        model_config=model_config,
        max_tokens_override=max_tokens_override,
    )
    provider = str(request_config.get("provider", "")).strip().lower()
    model_name = str(request_config.get("model_name", "")).strip()
    api_key = str(request_config.get("api_key", "")).strip()
    base_url = str(request_config.get("base_url", "")).strip() or "https://api.openai.com/v1"
    max_tokens = int(request_config.get("max_tokens", 4000) or 4000)

    if provider == "gemini" or model_name.lower().startswith("gemini"):
        raise RuntimeError("Direct HTTP fallback is not implemented for Gemini-compatible configs")
    if not _has_usable_api_key(api_key):
        raise RuntimeError(
            "No usable LLM API key configured for final polish. "
            "Pass --model-config-json/--model-config-file, configure an active model in ScienceClaw, or set DS_API_KEY."
        )

    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {response_body[:1000]}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from LLM gateway: {raw_body[:400]}") from exc

    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"LLM gateway returned no choices: {payload}")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = _extract_message_text(message.get("content", ""))
    if not str(content).strip():
        raise RuntimeError(f"LLM gateway returned empty content: {payload}")
    return str(content)


def _load_llm_config_from_mongo() -> dict[str, Any] | None:
    try:
        backend_root = _resolve_backend_root()
        if backend_root is None:
            raise RuntimeError("backend package not available")
        backend_root_str = str(backend_root)
        if backend_root_str not in sys.path:
            sys.path.insert(0, backend_root_str)
        from backend.config import settings
        from pymongo import MongoClient
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] unable to import Mongo-backed model config helpers: %s", exc)
        return None

    errors: list[str] = []
    for spec in _mongo_connection_specs(settings):
        mongo_client = None
        try:
            client_kwargs: dict[str, Any] = {
                "host": spec["host"],
                "port": spec["port"],
                "serverSelectionTimeoutMS": 3000,
            }
            if spec["username"]:
                client_kwargs["username"] = spec["username"]
            if spec["password"]:
                client_kwargs["password"] = spec["password"]
            if spec["username"] and spec["password"]:
                client_kwargs["authSource"] = "admin"

            mongo_client = MongoClient(**client_kwargs)
            database = mongo_client[spec["db_name"]]

            session_doc = database["sessions"].find_one(
                {"model_config.api_key": {"$exists": True, "$nin": ["", None]}},
                sort=[("updated_at", -1)],
                projection={"model_config": 1},
            )
            session_config = (session_doc or {}).get("model_config")
            if isinstance(session_config, dict) and _has_usable_api_key(session_config.get("api_key")):
                return _normalize_model_config_for_runtime(
                    {
                        "model_name": session_config.get("model_name"),
                        "base_url": session_config.get("base_url"),
                        "api_key": session_config.get("api_key"),
                        "context_window": session_config.get("context_window"),
                    }
                )

            model_doc = database["models"].find_one(
                {"api_key": {"$exists": True, "$nin": ["", None]}, "is_active": True},
                sort=[("updated_at", -1)],
                projection={"model_name": 1, "base_url": 1, "api_key": 1, "context_window": 1},
            )
            if isinstance(model_doc, dict) and _has_usable_api_key(model_doc.get("api_key")):
                return _normalize_model_config_for_runtime(
                    {
                        "model_name": model_doc.get("model_name"),
                        "base_url": model_doc.get("base_url"),
                        "api_key": model_doc.get("api_key"),
                        "context_window": model_doc.get("context_window"),
                    }
                )
        except Exception as exc:
            errors.append(f"{spec['source']}@{spec['host']}:{spec['port']} -> {exc}")
        finally:
            if mongo_client is not None:
                mongo_client.close()

    if errors:
        logger.warning(
            "[obsidian_run_zotero_review_agent] failed to resolve tool LLM config from Mongo: %s",
            " | ".join(errors),
        )
    return None


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = text.replace("\x00", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", _clean_text(text)).strip()


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _safe_slug(value: str, fallback: str = "review-agent") -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-_")
    return slug or fallback


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def _strip_markdown_fence(text: str) -> str:
    stripped = str(text or "").strip()
    match = re.match(r"^```(?:markdown|md)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def _truncate_text(value: Any, limit: int = 320) -> str:
    text = _normalize_whitespace(str(value or ""))
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip(" ,;:，；：")
    return clipped + "…"


def _truncate_block_text(value: Any, limit: int = 4000) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_authors(value: Any) -> str:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "；".join(items)
    return _truncate_text(value, limit=180)


def _skills_root() -> Path:
    for candidate in _skill_root_candidates():
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent.parent / "Skills"


def _skill_root_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("EXTERNAL_SKILLS_DIR", "SKILLS_DIR"):
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            candidates.append(Path(raw))
    candidates.extend(
        [
            Path(__file__).resolve().parent.parent / "Skills",
            Path("/app/Skills"),
            Path("/skills"),
            Path.cwd() / "Skills",
        ]
    )
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        raw = str(candidate).strip()
        if not raw:
            continue
        key = candidate.as_posix() if candidate.is_absolute() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _find_skill_doc(skill_name: str) -> Path | None:
    for root in _skill_root_candidates():
        skill_path = root / skill_name / "SKILL.md"
        if skill_path.exists():
            return skill_path
    return None


def _read_required_skill_docs(required_skills: list[str]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    docs: list[dict[str, str]] = []
    read_skills: list[str] = []
    missing_skills: list[str] = []
    for skill_name in required_skills:
        skill_path = _find_skill_doc(skill_name)
        if skill_path is None:
            missing_skills.append(skill_name)
            continue
        docs.append(
            {
                "name": skill_name,
                "path": str(skill_path),
                "content": skill_path.read_text(encoding="utf-8"),
            }
        )
        read_skills.append(skill_name)
    return docs, read_skills, missing_skills


def _summarize_page_excerpts(paper: dict[str, Any], max_items: int = 2) -> str:
    excerpts = paper.get("page_excerpts", [])
    if not isinstance(excerpts, list):
        return "无页面摘录"
    lines: list[str] = []
    for row in excerpts[:max_items]:
        if not isinstance(row, dict):
            continue
        page_label = str(row.get("page_label", "")).strip() or "未标页"
        section = str(row.get("section", "")).strip() or "evidence"
        excerpt = _truncate_text(row.get("excerpt", ""), limit=220)
        if excerpt:
            lines.append(f"{page_label} / {section}: {excerpt}")
    return " | ".join(lines) if lines else "无页面摘录"


def _paper_prompt_block(index: int, paper: dict[str, Any]) -> str:
    title = str(paper.get("title", "")).strip() or "Untitled"
    year = str(paper.get("year", "")).strip() or "n.d."
    citekey = str(paper.get("citekey", "")).strip()
    note_path = str(paper.get("relative_note_path", "")).strip()
    theme = str(paper.get("theme_label", "")).strip() or "未分组"
    relevance = str(paper.get("relevance_label", "")).strip() or "unknown"
    authors = _normalize_authors(paper.get("authors", []))
    return "\n".join(
        [
            f"{index}. {title} ({year})",
            f"   citekey: {citekey or 'n/a'}",
            f"   authors: {authors or 'n/a'}",
            f"   note: {note_path or 'n/a'}",
            f"   theme: {theme}",
            f"   relevance: {relevance}",
            f"   summary: {_truncate_text(paper.get('one_sentence_summary', ''), limit=220) or 'n/a'}",
            f"   methods: {_truncate_text(paper.get('methods_summary', ''), limit=260) or 'n/a'}",
            f"   findings: {_truncate_text(paper.get('key_findings', ''), limit=280) or 'n/a'}",
            f"   limitations: {_truncate_text(paper.get('limitations', ''), limit=220) or 'n/a'}",
            f"   page_evidence: {_summarize_page_excerpts(paper)}",
        ]
    )


def _build_evidence_brief(writing_input: dict[str, Any]) -> str:
    topic = str(writing_input.get("topic", "")).strip()
    keywords = "、".join(str(item).strip() for item in writing_input.get("keywords", []) if str(item).strip())
    warnings = writing_input.get("warnings", [])
    warning_text = "\n".join(f"- {str(item).strip()}" for item in warnings if str(item).strip()) or "- 无"
    pdf_stats = writing_input.get("pdf_stats", {}) if isinstance(writing_input.get("pdf_stats"), dict) else {}
    core_papers = writing_input.get("core_papers", []) if isinstance(writing_input.get("core_papers"), list) else []
    boundary_papers = writing_input.get("boundary_papers", []) if isinstance(writing_input.get("boundary_papers"), list) else []
    noise_papers = writing_input.get("noise_papers", []) if isinstance(writing_input.get("noise_papers"), list) else []
    section_hints = writing_input.get("section_hints", []) if isinstance(writing_input.get("section_hints"), list) else []
    section_text = "、".join(str(item).strip() for item in section_hints if str(item).strip()) or "未提供"
    lines = [
        f"主题: {topic or '未命名主题'}",
        f"关键词: {keywords or '未提供'}",
        f"纳入文献: core={len(core_papers)}, boundary={len(boundary_papers)}, noise={len(noise_papers)}",
        "PDF统计:",
        f"- total_papers={int(pdf_stats.get('total_papers', 0) or 0)}",
        f"- accessible_pdf_count={int(pdf_stats.get('accessible_pdf_count', 0) or 0)}",
        f"- fulltext_ready_count={int(pdf_stats.get('fulltext_ready_count', 0) or 0)}",
        f"- missing_pdf_count={int(pdf_stats.get('missing_pdf_count', 0) or 0)}",
        f"- metadata_conflict_count={int(pdf_stats.get('metadata_conflict_count', 0) or 0)}",
        f"section_hints: {section_text}",
        "warnings:",
        warning_text,
        "",
        "核心文献:",
    ]
    lines.extend(_paper_prompt_block(index, paper) for index, paper in enumerate(core_papers[:8], start=1))
    if boundary_papers:
        lines.extend(["", "边界文献:"])
        lines.extend(
            _paper_prompt_block(index, paper)
            for index, paper in enumerate(boundary_papers[:5], start=1)
        )
    if noise_papers:
        lines.extend(["", "排除/噪声文献:"])
        for index, paper in enumerate(noise_papers[:3], start=1):
            title = str(paper.get("title", "")).strip() or "Untitled"
            reason = str(paper.get("relevance_reason", "")).strip() or str(paper.get("relevance_label", "")).strip() or "未说明"
            lines.append(f"{index}. {title} - {reason}")
    return "\n".join(lines).strip()


def _skill_docs_block(skill_docs: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for doc in skill_docs:
        blocks.append(
            "\n".join(
                [
                    f"=== {doc['name']} ===",
                    f"path: {doc['path']}",
                    doc["content"].strip(),
                ]
            )
        )
    return "\n\n".join(blocks).strip()


def _sanitize_polished_review(topic: str, markdown: str) -> str:
    cleaned = _strip_markdown_fence(markdown).replace("\r", "\n").strip()
    cleaned = re.sub(r"(?ms)^> \[!info\].*?(?:\n\n|$)", "", cleaned).strip()
    if not re.search(r"(?m)^#\s+", cleaned):
        cleaned = f"# {topic}\n\n{cleaned}"
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def _count_present_sections(markdown: str) -> int:
    return sum(1 for heading in _REVIEW_SECTION_HEADINGS if heading in markdown)


def _is_retryable_llm_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    retry_markers = (
        "error code: 500",
        "error code: 502",
        "error code: 503",
        "error code: 504",
        "bad gateway",
        "gateway timeout",
        "timed out",
        "timeout",
        "connection reset",
        "temporarily unavailable",
    )
    return any(marker in text for marker in retry_markers)


def _polish_review_with_local_skills(
    topic: str,
    draft_markdown: str,
    writing_input: dict[str, Any],
    revision_request: str = "",
    current_body: str = "",
    review_note_path: str = "",
    model_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skill_docs, read_skills, missing_skills = _read_required_skill_docs(list(_REQUIRED_LOCAL_SKILLS))
    if missing_skills:
        return {
            "ok": False,
            "error": "Missing required local skills: " + ", ".join(missing_skills),
            "read_skills": read_skills,
            "missing_required_skills": missing_skills,
        }

    system_prompt = (
        "你是 ScienceClaw 的 Zotero/Obsidian 中文综述写作器。"
        "你的工作不是照抄 PDF/OCR 原文，而是严格依据本地证据进行综述性综合。"
        "你必须先遵循提供的 5 个本地 skill，再输出最终 Markdown。"
        "禁止捏造事实、引用、页码、实验结果；证据不充分时要明确写成局限。"
        "最终输出必须是适合 Obsidian 的中文综述正文，不要输出解释、前言或代码围栏。"
    )
    evidence_brief = _build_evidence_brief(writing_input)
    request_line = revision_request.strip() or "请生成第一版正式中文综述，并使其像真实文献综述而不是工具拼接稿。"
    user_prompt = "\n\n".join(
        [
            "请严格按以下顺序使用本地技能："
            "1. zotero-materials-review"
            " 2. literature-review"
            " 3. scientific-writing"
            " 4. obsidian-markdown"
            " 5. materials-obsidian",
            "本地 skill 文档如下，请把它们当作刚刚读取过的工作流说明：\n" + _skill_docs_block(skill_docs),
            f"任务主题: {topic}",
            f"当前 review note 路径: {review_note_path or str(writing_input.get('review_note_path', '')).strip() or '未提供'}",
            f"用户要求: {request_line}",
            "输出要求:\n"
            "- 只输出 Markdown 正文，不要 ```markdown 包裹。\n"
            "- 只保留一个一级标题 `# 主题`。\n"
            "- 正文必须是中文学术段落，不要逐篇论文 bullet dump。\n"
            "- 不要保留“生成说明”或 workflow callout。\n"
            "- 不要直接粘贴大段英文 PDF 原文，必须先消化后用中文综合表达。\n"
            "- `## 参考文献` 使用编号条目；若已有作者/年份/题名则尽量组织成接近 GB/T 7714 的形式，缺失字段不要杜撰。\n"
            "- 若存在 `relative_note_path`，可在参考文献条目末尾追加对应的 Obsidian wikilink 便于追溯。\n"
            "- 至少覆盖以下章节：\n  "
            + "\n  ".join(_REVIEW_SECTION_HEADINGS),
            "结构化证据摘要:\n" + evidence_brief,
            "现有草稿:\n" + _truncate_block_text(draft_markdown, limit=12000),
            "当前笔记正文（如有）:\n" + (_truncate_block_text(current_body, limit=5000) or "无"),
        ]
    )

    fallback_markdown = _sanitize_polished_review(topic, draft_markdown)
    try:
        llm = _load_llm_model(
            model_config=model_config,
            max_tokens_override=_REVIEW_POLISH_MAX_TOKENS,
        )
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] unable to load tool LLM, using structured draft fallback: %s", exc)
        return {
            "ok": True,
            "markdown": fallback_markdown,
            "read_skills": read_skills,
            "missing_required_skills": [],
            "writing_pass": "template-draft",
            "llm_fallback_reason": str(exc),
        }
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    last_markdown = ""
    for attempt in range(2):
        try:
            response = llm.invoke(messages)
        except Exception as exc:
            if attempt == 0 and _is_retryable_llm_error(exc):
                logger.warning(
                    "[obsidian_run_zotero_review_agent] transient LLM invoke failure on attempt %s/2, retrying once: %s",
                    attempt + 1,
                    exc,
                )
                continue
            try:
                direct_content = _invoke_openai_compatible_llm_via_http(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_config=model_config,
                    max_tokens_override=_REVIEW_POLISH_MAX_TOKENS,
                )
                response = direct_content
            except Exception as direct_exc:
                logger.warning(
                    "[obsidian_run_zotero_review_agent] LLM invoke failed, and direct HTTP fallback also failed: %s | fallback=%s",
                    exc,
                    direct_exc,
                )
                return {
                    "ok": True,
                    "markdown": fallback_markdown,
                    "read_skills": read_skills,
                    "missing_required_skills": [],
                    "writing_pass": "template-draft",
                    "llm_fallback_reason": str(exc),
                }
        candidate = _sanitize_polished_review(topic, _extract_message_text(getattr(response, "content", response)))
        last_markdown = candidate
        if _count_present_sections(candidate) >= 7:
            return {
                "ok": True,
                "markdown": candidate,
                "read_skills": read_skills,
                "missing_required_skills": [],
                "writing_pass": "scientific-writing",
            }
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=user_prompt
                + "\n\n你上一版输出的章节结构不完整。请完整重写，确保九个主章节齐全，并维持中文学术综述风格。"
            ),
        ]

    logger.warning(
        "[obsidian_run_zotero_review_agent] LLM rewrite produced incomplete structure, using deterministic draft fallback"
    )
    return {
        "ok": True,
        "markdown": fallback_markdown,
        "read_skills": read_skills,
        "missing_required_skills": [],
        "writing_pass": "template-draft",
        "llm_fallback_reason": "Skill-driven rewrite produced incomplete review structure",
        "raw_markdown": last_markdown,
    }


def _validate_bbt_export(payload: Any) -> tuple[bool, str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return False, "Expected Better BibTeX export to be a JSON object", []

    items = payload.get("items", [])
    if not isinstance(items, list):
        return False, "Expected `items` to be a list in Better BibTeX export", []

    parent_items = [
        item for item in items
        if isinstance(item, dict) and str(item.get("itemType", "")).strip().lower() not in _SKIP_ITEM_TYPES
    ]
    if not parent_items:
        return False, "No parent references found in Better BibTeX export", []
    return True, "", parent_items


def _summarize_pages(row: dict[str, Any]) -> str:
    pages = row.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return "未记录页码"
    if len(pages) == 1:
        return f"第 {pages[0]} 页"
    return "第 " + "、".join(str(page) for page in pages) + " 页"


def _make_page_excerpt(section: str, row: dict[str, Any], excerpt: str) -> dict[str, Any]:
    return {
        "section": section,
        "pages": row.get("pages", []) if isinstance(row.get("pages", []), list) else [],
        "page_label": _summarize_pages(row),
        "excerpt": _clean_text(excerpt),
    }


def _guess_theme_label(paper: dict[str, Any]) -> str:
    text = "\n".join(
        [
            str(paper.get("title", "")),
            str(paper.get("one_sentence_summary", "")),
            str(paper.get("methods_summary", "")),
            str(paper.get("key_findings", "")),
        ]
    ).lower()

    if any(token in text for token in ("agent", "workflow", "assistant", "copilot", "autonomous")):
        return "智能代理与科研工作流"
    if any(token in text for token in ("llm", "language model", "large language", "gpt", "instruction")):
        return "大语言模型与知识组织"
    if any(token in text for token in ("diffusion", "generative", "gan", "mattergen", "design")):
        return "生成模型驱动的设计与发现"
    if any(token in text for token in ("multimodal", "vision", "graph", "retrieval", "rag")):
        return "多模态建模与知识增强"
    if any(token in text for token in ("benchmark", "evaluation", "survey", "review", "assessment")):
        return "评测基准与方法比较"
    return "交叉方法与应用场景"


def _format_wikilink(paper: dict[str, Any]) -> str:
    note_path = str(paper.get("relative_note_path", "")).strip()
    title = _normalize_whitespace(str(paper.get("title", "")).strip()) or str(paper.get("citekey", "")).strip() or "未命名文献"
    year = str(paper.get("year", "")).strip()
    if note_path:
        rendered = f"[[{note_path}|{title}]]"
    else:
        rendered = f"《{title}》"
    if year:
        return f"{rendered}（{year}）"
    return rendered


def _format_reference_line(paper: dict[str, Any], index: int | None = None) -> str:
    title = _normalize_whitespace(str(paper.get("title", "")).strip()) or str(paper.get("citekey", "")).strip() or "Untitled"
    year = str(paper.get("year", "")).strip()
    doi = str(paper.get("doi", "")).strip()
    note_path = str(paper.get("relative_note_path", "")).strip()
    prefix = f"{index}. " if index is not None else ""
    parts = [f"{prefix}{title}"]
    if year:
        parts.append(f"({year})")
    if doi:
        parts.append(f"DOI: {doi}")
    if note_path:
        parts.append(f"[[{note_path}|文献笔记]]")
    return " ".join(parts).strip()


def _collect_top_keywords(papers: list[dict[str, Any]], topic: str) -> list[str]:
    counter: Counter[str] = Counter()
    theme_counter: Counter[str] = Counter()
    for paper in papers:
        theme_label = str(paper.get("theme_label", "")).strip()
        if theme_label:
            theme_counter[theme_label] += 1
        corpus = "\n".join(
            [
                str(paper.get("title", "")),
                str(paper.get("one_sentence_summary", "")),
                str(paper.get("methods_summary", "")),
            ]
        ).lower()
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", corpus):
            if token in {
                "and", "for", "the", "with", "from", "using", "that", "this",
                "review", "survey", "materials", "material", "model", "models",
                "language", "learning", "crystal", "design", "large",
            }:
                continue
            counter[token] += 1

    keywords = [topic.strip()] if topic.strip() else []
    for theme, _count in theme_counter.most_common():
        for keyword in _THEME_KEYWORD_MAP.get(theme, []):
            if keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 5:
                break
        if len(keywords) >= 5:
            break
    if len(keywords) >= 5:
        if "文献综述" not in keywords:
            keywords.append("文献综述")
        return keywords[:6]
    for token, _count in counter.most_common(5):
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= 5:
            break
    if "文献综述" not in keywords:
        keywords.append("文献综述")
    return keywords[:6]


def _paper_payload(summary: dict[str, Any], evidence: dict[str, Any], imported_note_path: str) -> dict[str, Any]:
    intro_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "introduction"
        ),
        {},
    )
    methods_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "methods"
        ),
        {},
    )
    findings_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "findings"
        ),
        {},
    )
    return {
        "title": str(evidence.get("title", "") or summary.get("title", "")).strip(),
        "citekey": str(evidence.get("citekey", "") or summary.get("citekey", "")).strip(),
        "year": str(evidence.get("year", "") or summary.get("year", "")).strip(),
        "doi": str(evidence.get("doi", "") or summary.get("doi", "")).strip(),
        "relative_note_path": imported_note_path,
        "one_sentence_summary": str(evidence.get("one_sentence_summary", "") or summary.get("one_sentence_summary", "")).strip(),
        "abstract": _clean_text(evidence.get("abstract_from_json", "")),
        "fulltext_excerpt": _clean_text(evidence.get("fulltext_excerpt", "")),
        "methods_summary": _clean_text(evidence.get("methods_summary", "")),
        "key_findings": _clean_text(evidence.get("key_findings", "")),
        "limitations": _clean_text(evidence.get("limitations", "")),
        "section_hint": str(evidence.get("section_hint", "") or summary.get("section_hint", "")).strip(),
        "theme_label": _guess_theme_label(evidence),
        "preferred_summary_source": str(evidence.get("preferred_summary_source", "")).strip(),
        "attachment_pdf_path": str(evidence.get("attachment_pdf_path", "")).strip(),
        "metadata_conflict": bool(evidence.get("metadata_conflict", False)),
        "metadata_conflict_reason": str(evidence.get("metadata_conflict_reason", "")).strip(),
        "relevance_label": str(evidence.get("relevance_label", "") or summary.get("relevance_label", "")).strip(),
        "relevance_reason": str(evidence.get("relevance_reason", "") or summary.get("relevance_reason", "")).strip(),
        "page_excerpts": [
            _make_page_excerpt("introduction", intro_row, evidence.get("fulltext_excerpt", "")),
            _make_page_excerpt("methods", methods_row, evidence.get("methods_summary", "")),
            _make_page_excerpt("findings", findings_row, evidence.get("key_findings", "")),
        ],
        "source_diagnostics": evidence.get("source_diagnostics", {}),
    }


def _load_paper_payloads(
    bundle: dict[str, Any],
    evidence_dir: Path,
    imported_note_paths: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    evidence_map: dict[str, dict[str, Any]] = {}
    for evidence_file in sorted(evidence_dir.glob("*.json")):
        try:
            evidence = _load_json(evidence_file)
        except Exception as exc:
            logger.warning("[obsidian_run_zotero_review_agent] failed to read evidence %s: %s", evidence_file, exc)
            continue
        citekey = str(evidence.get("citekey", "")).strip()
        if citekey:
            evidence_map[citekey] = evidence

    payloads: dict[str, list[dict[str, Any]]] = {"core": [], "boundary": [], "noise": []}
    for label in ("core", "boundary", "noise"):
        for row in bundle.get(f"{label}_papers", []) or []:
            if not isinstance(row, dict):
                continue
            citekey = str(row.get("citekey", "")).strip()
            evidence = evidence_map.get(citekey, {})
            payloads[label].append(
                _paper_payload(
                    summary=row,
                    evidence=evidence,
                    imported_note_path=imported_note_paths.get(citekey, ""),
                )
            )
    return payloads


def _build_pdf_stats(payloads: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_papers = payloads["core"] + payloads["boundary"] + payloads["noise"]
    method_counter: Counter[str] = Counter()
    missing_pdf_titles: list[str] = []
    accessible_pdf_count = 0
    fulltext_ready_count = 0
    metadata_conflict_count = 0

    for paper in all_papers:
        diagnostics = paper.get("source_diagnostics", {}) or {}
        extraction_method = str(diagnostics.get("extraction_method", "")).strip()
        if extraction_method:
            method_counter[extraction_method] += 1
            fulltext_ready_count += 1
        if str(paper.get("attachment_pdf_path", "")).strip():
            accessible_pdf_count += 1
        if diagnostics.get("pdf_unavailable"):
            missing_pdf_titles.append(str(paper.get("title", "")).strip() or "Untitled")
        if paper.get("metadata_conflict"):
            metadata_conflict_count += 1

    return {
        "total_papers": len(all_papers),
        "accessible_pdf_count": accessible_pdf_count,
        "fulltext_ready_count": fulltext_ready_count,
        "missing_pdf_count": len(missing_pdf_titles),
        "missing_pdf_titles": missing_pdf_titles,
        "extraction_method_counts": dict(method_counter),
        "metadata_conflict_count": metadata_conflict_count,
    }


def _build_warnings(
    import_result: dict[str, Any],
    pdf_stats: dict[str, Any],
    payloads: dict[str, list[dict[str, Any]]],
) -> list[str]:
    warnings: list[str] = []
    skipped_count = int(import_result.get("skipped_count", 0) or 0)
    if skipped_count:
        warnings.append(f"有 {skipped_count} 篇条目在导入文献笔记时被跳过，请检查是否已存在同名笔记或写入失败。")

    missing_pdf_count = int(pdf_stats.get("missing_pdf_count", 0) or 0)
    if missing_pdf_count:
        warnings.append(f"有 {missing_pdf_count} 篇文献未找到可访问 PDF，相关综述内容将更多依赖导出摘要。")

    conflict_count = int(pdf_stats.get("metadata_conflict_count", 0) or 0)
    if conflict_count:
        warnings.append(f"检测到 {conflict_count} 篇文献存在题目与摘要语义不一致，已优先使用全文片段。")

    if not payloads["core"] and payloads["boundary"]:
        warnings.append("当前主题下没有明显核心文献，本次综述主要依据边界相关文献组织。")
    if not (payloads["core"] or payloads["boundary"]):
        warnings.append("没有筛选出可纳入综述的文献，请检查导出主题是否正确。")
    return warnings


def _render_theme_section(theme: str, papers: list[dict[str, Any]]) -> str:
    if not papers:
        return ""

    citations = "、".join(_format_wikilink(paper) for paper in papers[:3])
    years = sorted(
        {
            int(str(paper.get("year", "")).strip())
            for paper in papers
            if str(paper.get("year", "")).strip().isdigit()
        }
    )
    year_text = ""
    if years:
        if years[0] == years[-1]:
            year_text = f"从时间分布看，该方向主要集中在 {years[0]} 年。"
        else:
            year_text = f"从时间分布看，该方向主要覆盖 {years[0]} 至 {years[-1]} 年。"

    paragraph = (
        f"### {theme}\n\n"
        f"{_THEME_OVERVIEW_MAP.get(theme, '这一方向体现了当前主题在不同任务场景中的方法扩展与应用深化。')}"
        f"当前纳入的代表性工作包括{citations}。"
    )
    if year_text:
        paragraph += year_text
    paragraph += _THEME_COMPARISON_MAP.get(theme, "这类工作共同体现了该主题从方法探索走向场景化应用与系统化比较的趋势。")
    if len(papers) >= 4:
        paragraph += f"目前该方向共纳入 {len(papers)} 篇文献，说明它已成为当前主题中占比较高的研究分支。"
    return paragraph.strip()


def _render_challenge_paragraph(
    topic: str,
    papers: list[dict[str, Any]],
    pdf_stats: dict[str, Any],
    warnings: list[str],
) -> str:
    theme_counter = Counter(
        str(paper.get("theme_label", "")).strip()
        for paper in papers
        if str(paper.get("theme_label", "")).strip()
    )
    challenge_bits: list[str] = []
    if theme_counter.get("评测基准与方法比较", 0):
        challenge_bits.append("虽然已有基准化研究出现，但任务定义、数据拆分与评价指标口径仍未完全统一")
    else:
        challenge_bits.append("当前主题仍缺少足够稳定的统一 benchmark 来支撑横向比较")
    challenge_bits.append("不同方法分支之间的输入表示、目标性质和验证流程差异较大，导致结果可比性有限")
    if int(pdf_stats.get("missing_pdf_count", 0) or 0):
        challenge_bits.append(
            f"仍有 {int(pdf_stats.get('missing_pdf_count', 0) or 0)} 篇文献缺少可访问全文，部分判断只能保守依赖摘要与元数据"
        )
    if warnings:
        challenge_bits.append("自动化链路虽然能显著提高整理效率，但关键论断与引用细节仍需要人工复核")
    return f"围绕“{topic}”的现有研究，主要挑战可概括为" + "；".join(challenge_bits) + "。"


def _render_future_paragraph(topic: str, payloads: dict[str, list[dict[str, Any]]], pdf_stats: dict[str, Any]) -> str:
    boundary_papers = payloads.get("boundary") or payloads.get("boundary_papers") or []
    core_papers = payloads.get("core") or payloads.get("core_papers") or []
    opportunities: list[str] = []
    if int(pdf_stats.get("missing_pdf_count", 0) or 0):
        opportunities.append("补全缺失全文并重新核对证据页码")
    if boundary_papers:
        opportunities.append("围绕边界文献建立更清晰的纳入/排除标准")
    if core_papers:
        opportunities.append("把核心文献中的方法链路和评价指标整理成统一比较框架")
    if any(str(paper.get("theme_label", "")).strip() == "大语言模型与知识组织" for paper in core_papers):
        opportunities.append("推动大语言模型与结构化材料表征、实验数据和知识图谱进一步协同")
    if any(str(paper.get("theme_label", "")).strip() == "生成模型驱动的设计与发现" for paper in core_papers):
        opportunities.append("把生成设计结果与可验证的性质预测和实验约束联动起来")
    opportunities.append("将综述结论继续沉淀为 Obsidian 项目笔记与写作提纲")
    return f"针对“{topic}”主题，下一步更有价值的工作包括" + "、".join(opportunities) + "。"


def _render_review_draft(topic: str, export_path: Path, writing_input: dict[str, Any], pdf_stats: dict[str, Any]) -> str:
    core_papers = writing_input.get("core_papers", [])
    boundary_papers = writing_input.get("boundary_papers", [])
    included_papers = writing_input.get("included_papers", [])
    noise_papers = writing_input.get("noise_papers", [])
    theme_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in included_papers:
        theme_map[str(paper.get("theme_label", "")).strip() or "交叉方法与应用场景"].append(paper)

    keywords = writing_input.get("keywords", [])
    keyword_line = "；".join(str(keyword).strip() for keyword in keywords if str(keyword).strip())
    theme_counts = sorted(theme_map.items(), key=lambda item: (-len(item[1]), item[0]))
    theme_summary = "、".join(f"{theme}（{len(papers)}篇）" for theme, papers in theme_counts[:4]) or "交叉方法与应用场景"
    section_hints: list[str] = []
    for item in writing_input.get("section_hints", []):
        if isinstance(item, dict):
            heading = str(item.get("heading", "")).strip()
            if heading:
                section_hints.append(heading)
            continue
        text = str(item).strip()
        if text:
            section_hints.append(text)

    abstract_lines = [
        f"本文基于本地 Zotero Better BibTeX 导出 `{export_path}` 及其可访问附件 PDF，对“{topic}”相关文献进行了自动化整理与回写。",
        f"本轮共处理 {writing_input.get('processed_parent_items', 0)} 篇父条目，其中核心文献 {len(core_papers)} 篇、边界文献 {len(boundary_papers)} 篇、排除文献 {len(noise_papers)} 篇。",
        f"在证据层面，共有 {pdf_stats.get('fulltext_ready_count', 0)} 篇文献具备可读全文，其余条目主要依赖导出摘要与元数据补足。",
        f"从当前纳入结果看，该主题主要围绕{theme_summary}等方向展开，研究重心已从单点方法探索逐步扩展到基准评测、知识组织和科研工作流协同。",
    ]

    intro = (
        f"本综述以本地知识管理链路为基础，结合 Zotero 导出的题录、摘要、附件路径以及 Obsidian 文献卡片，对“{topic}”主题进行可追溯整理。"
        f"与只依赖摘要的快速综述不同，本次流程优先读取可访问 PDF 全文，再将导入结果与综述笔记统一回写到 Obsidian，"
        f"从而保证后续写作、继续阅读和项目沉淀时仍能追溯到原始文献证据。"
    )

    foundations = (
        f"从现有纳入文献看，该主题的技术基础并非单一路线，而是由{theme_summary}等分支共同构成。"
        f"如果按研究链路理解，这些工作大致覆盖{('、'.join(section_hints[:4]) if section_hints else '任务定义、方法建模、评测验证与知识组织')}等层面。"
        f"在证据可得性方面，本轮有 {pdf_stats.get('fulltext_ready_count', 0)} 篇文献具备可读全文，"
        f"说明当前综述不仅依赖题录元数据，也能够参考全文证据组织结构化判断。"
    )

    if theme_counts:
        comparison_bits = [
            _THEME_COMPARISON_MAP.get(theme, f"{theme}方向体现出明显的方法与任务差异").rstrip("。；;.!? ")
            for theme, _papers in theme_counts[:3]
        ]
        comparison = (
            "从代表性工作比较来看，"
            + "；".join(comparison_bits)
            + "。这说明当前领域的关键差异不只体现在模型本身，也体现在数据组织方式、评价口径和研究目标设定上。"
        )
    else:
        comparison = "当前代表性工作之间的差异主要体现在研究对象、评价指标以及是否具备完整全文证据三个层面。"

    references = "\n".join(
        _format_reference_line(paper, index)
        for index, paper in enumerate(included_papers, start=1)
    ) or "1. 暂无可引用文献。"

    theme_sections = "\n\n".join(
        section for section in (
            _render_theme_section(theme, papers)
            for theme, papers in sorted(theme_map.items(), key=lambda item: (-len(item[1]), item[0]))
        )
        if section
    ) or "### 主要方向待补充\n\n当前尚未形成足够稳定的主题分组，建议先补全全文后再细化方向章节。"

    challenge_text = _render_challenge_paragraph(
        topic=topic,
        papers=included_papers,
        pdf_stats=pdf_stats,
        warnings=writing_input.get("warnings", []),
    )
    future_text = _render_future_paragraph(topic, writing_input, pdf_stats)
    conclusion_text = (
        f"总体而言，围绕“{topic}”的现有研究已经形成从方法探索到基准比较、再到科研工作流集成的多层次格局。"
        f"对当前知识库而言，更重要的是继续在统一结构下沉淀 literature notes 与 review notes，并在后续写作中逐条复核关键论断与引用细节。"
    )

    return "\n".join(
        [
            f"# {topic}",
            "",
            "## 摘要",
            " ".join(abstract_lines),
            "",
            "## 关键词",
            keyword_line or "待补充",
            "",
            "## 引言",
            intro,
            "",
            "## 技术基础与发展脉络",
            foundations,
            "",
            "## 主要研究方向",
            theme_sections,
            "",
            "## 代表性工作比较与讨论",
            comparison,
            "",
            "## 挑战与争议",
            challenge_text,
            "",
            "## 未来趋势与机会",
            future_text,
            "",
            "## 结论",
            conclusion_text,
            "",
            "## 参考文献",
            references,
            "",
        ]
    ).strip() + "\n"


def _write_review_artifacts(
    export_path: Path,
    topic: str,
    writing_input: dict[str, Any],
    draft_markdown: str,
    artifacts_dir: str = "",
) -> tuple[str, str]:
    slug = _safe_slug(topic, "review-agent")
    research_data_dir = Path(str(artifacts_dir or "").strip()) if str(artifacts_dir or "").strip() else (
        export_path.parent.parent / "research_data" if export_path.parent.name.lower() == "zotero" else export_path.parent / "research_data"
    )
    research_data_dir.mkdir(parents=True, exist_ok=True)

    review_input_path = research_data_dir / f"{slug}-review-agent-input.json"
    review_input_path.write_text(json.dumps(writing_input, ensure_ascii=False, indent=2), encoding="utf-8")

    review_draft_path = research_data_dir / f"{slug}-review-agent-draft.md"
    review_draft_path.write_text(draft_markdown, encoding="utf-8")
    return str(review_input_path), str(review_draft_path)


@tool
def obsidian_run_zotero_review_agent(
    export_json_path: str,
    topic: str = "",
    category: str = "",
    vault_dir: str = "",
    overwrite_existing: bool = False,
    max_items: int = 0,
    model_config_json: str = "",
) -> dict:
    """Run the local Zotero -> review-bundle -> Chinese review -> Obsidian workflow.

    Use this tool when the user wants an end-to-end Zotero Review Agent run:
    validate a Better BibTeX export, build full-text evidence, generate/update
    literature and review notes in Obsidian, and prepare a structured review
    writing package for follow-up refinement.
    """
    logger.info(
        "[obsidian_run_zotero_review_agent] export_json_path=%r topic=%r vault_dir=%r overwrite_existing=%s max_items=%s has_model_config=%s",
        export_json_path,
        topic,
        vault_dir,
        overwrite_existing,
        max_items,
        bool(str(model_config_json or "").strip()),
    )

    try:
        resolved_model_config = _parse_model_config_json(model_config_json)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    export_path = _resolve_path(export_json_path)
    if not export_path.exists():
        return {"ok": False, "error": f"Export JSON not found: {export_path}"}

    try:
        payload = _load_json(export_path)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON: {exc}"}

    valid, validation_error, parent_items = _validate_bbt_export(payload)
    if not valid:
        return {"ok": False, "error": validation_error}

    resolved_topic = topic.strip() or export_path.stem
    resolved_category = _normalize_category(category, resolved_topic)
    build_bundle = _load_bundle_tool()
    import_tool = _load_import_tool()
    writer_tool = _load_writer_tool()

    bundle_result = build_bundle.invoke(
        {
            "export_json_path": str(export_path),
            "topic": resolved_topic,
            "category": resolved_category,
            "language": "zh",
            "prefer_pdf_fulltext": True,
            "relevance_policy": "balanced",
            "max_items": max_items,
        }
    )
    if not bundle_result.get("ok"):
        return {
            "ok": False,
            "error": bundle_result.get("error", "Failed to build Zotero review bundle"),
            "topic": resolved_topic,
        }

    import_result = import_tool.invoke(
        {
            "export_json_path": str(export_path),
            "topic": resolved_topic,
            "category": resolved_category,
            "max_items": max_items,
            "vault_dir": vault_dir,
            "overwrite_existing": overwrite_existing,
            "create_review_note": True,
        }
    )
    if not import_result.get("ok"):
        return {
            "ok": False,
            "error": import_result.get("error", "Failed to import Zotero export into Obsidian"),
            "topic": resolved_topic,
            "bundle_path": bundle_result.get("review_bundle_path", ""),
            "bootstrap_result": import_result.get("bootstrap_result"),
            **_vault_result_fields(
                import_result,
                requested_default=str(vault_dir or "").strip(),
            ),
            "required_skills": import_result.get("required_skills", _REQUIRED_LOCAL_SKILLS),
            "read_skills": import_result.get("read_skills", []),
            "missing_required_skills": import_result.get("missing_required_skills", []),
        }

    import_vault_fields = _vault_result_fields(
        import_result,
        requested_default=str(vault_dir or "").strip(),
    )

    if not overwrite_existing and not str(import_result.get("review_note_path", "")).strip():
        return {
            "ok": False,
            "error": (
                f"Review note already exists for topic '{resolved_topic}'. "
                "Set overwrite_existing=true to replace it."
            ),
            "topic": resolved_topic,
            "bundle_path": str(bundle_result.get("review_bundle_path", "")),
            **import_vault_fields,
            "required_skills": import_result.get("required_skills", _REQUIRED_LOCAL_SKILLS),
            "read_skills": import_result.get("read_skills", []),
            "missing_required_skills": import_result.get("missing_required_skills", []),
        }

    bundle_path = Path(str(bundle_result.get("review_bundle_path", "")))
    evidence_dir = Path(str(bundle_result.get("paper_evidence_dir", "")))
    if not bundle_path.exists():
        return {
            "ok": False,
            "error": f"Review bundle file missing after build step: {bundle_path}",
            "topic": resolved_topic,
        }
    bundle = _load_json(bundle_path)

    imported_note_paths = {
        str(row.get("citekey", "")).strip(): str(row.get("relative_note_path", "")).strip()
        for row in (import_result.get("imported_notes") or [])
        if isinstance(row, dict) and str(row.get("citekey", "")).strip()
    }
    payloads = _load_paper_payloads(bundle, evidence_dir, imported_note_paths)
    included_papers = payloads["core"] + payloads["boundary"]
    pdf_stats = _build_pdf_stats(payloads)

    writing_input = {
        "topic": resolved_topic,
        "category": resolved_category,
        "language": "zh",
        "source_export_json": str(export_path),
        "review_note_path": str(import_result.get("review_note_path", "")).strip(),
        "bundle_path": str(bundle_path),
        "paper_evidence_dir": str(evidence_dir),
        "processed_parent_items": int(bundle_result.get("processed_parent_items", len(parent_items)) or 0),
        "core_papers": payloads["core"],
        "boundary_papers": payloads["boundary"],
        "noise_papers": payloads["noise"],
        "included_papers": included_papers,
        "keywords": _collect_top_keywords(included_papers, resolved_topic),
        "metadata_conflicts": bundle.get("metadata_conflicts", []),
        "section_hints": bundle.get("section_hints", []),
        "pdf_stats": pdf_stats,
        "imported_notes": import_result.get("imported_notes", []),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
        "required_skills": list(_REQUIRED_LOCAL_SKILLS),
        "read_skills": [],
        "missing_required_skills": list(_REQUIRED_LOCAL_SKILLS),
    }

    warnings = _build_warnings(import_result, pdf_stats, payloads)
    writing_input["warnings"] = warnings

    template_markdown = _render_review_draft(
        topic=resolved_topic,
        export_path=export_path,
        writing_input=writing_input,
        pdf_stats=pdf_stats,
    )
    polish_result = _polish_review_with_local_skills(
        topic=resolved_topic,
        draft_markdown=template_markdown,
        writing_input=writing_input,
        review_note_path=str(import_result.get("review_note_path", "")).strip(),
        model_config=resolved_model_config,
    )
    if not polish_result.get("ok"):
        return {
            "ok": False,
            "error": polish_result.get("error", "Failed to run skill-driven final rewrite"),
            "topic": resolved_topic,
            "bundle_path": str(bundle_path),
            **import_vault_fields,
            "required_skills": list(_REQUIRED_LOCAL_SKILLS),
            "read_skills": polish_result.get("read_skills", []),
            "missing_required_skills": polish_result.get("missing_required_skills", list(_REQUIRED_LOCAL_SKILLS)),
        }
    writing_input["read_skills"] = polish_result.get("read_skills", [])
    writing_input["missing_required_skills"] = polish_result.get("missing_required_skills", [])
    llm_fallback_reason = str(polish_result.get("llm_fallback_reason", "")).strip()
    if llm_fallback_reason:
        warnings.append(f"Final review polish fell back to the structured draft: {llm_fallback_reason}")
        writing_input["warnings"] = warnings
    draft_markdown = str(polish_result.get("markdown", "")).strip()
    review_input_path, review_draft_path = _write_review_artifacts(
        export_path=export_path,
        topic=resolved_topic,
        writing_input=writing_input,
        draft_markdown=draft_markdown,
        artifacts_dir=str(bundle_path.parent),
    )

    review_metadata = {
        "title": resolved_topic,
        "topic": resolved_topic,
        "category": resolved_category,
        "keywords": writing_input["keywords"],
        "tags": ["materials-review", "zotero-review-agent", "zotero-import"],
        "review_bundle_path": str(bundle_path),
        "source_export_json": str(export_path),
        "writing_pass": str(polish_result.get("writing_pass", "scientific-writing")).strip() or "scientific-writing",
        "skill_pipeline": writing_input["skill_pipeline"],
        "required_skills": writing_input["required_skills"],
        "read_skills": writing_input["read_skills"],
        "missing_required_skills": writing_input["missing_required_skills"],
        "review_input_path": review_input_path,
        "review_draft_path": review_draft_path,
        "source_writing_input_path": review_input_path,
        "included_paper_count": len(included_papers),
        "boundary_paper_count": len(payloads["boundary"]),
        "noise_paper_count": len(payloads["noise"]),
        "pdf_stats": pdf_stats,
        "references": [
            {
                "title": paper.get("title", ""),
                "citekey": paper.get("citekey", ""),
                "year": paper.get("year", ""),
                "relative_note_path": paper.get("relative_note_path", ""),
                "one_sentence_summary": paper.get("one_sentence_summary", ""),
            }
            for paper in included_papers
        ],
    }
    final_review_result = writer_tool.invoke(
        {
            "note_type": "review",
            "title": resolved_topic,
            "content": draft_markdown,
            "metadata_json": json.dumps(review_metadata, ensure_ascii=False),
            "project_name": resolved_topic,
            "category": resolved_category,
            "vault_dir": vault_dir,
            "overwrite": True,
            "review_style": "survey_cn",
            "filename_style": "title-review",
            "conflict_mode": "error",
        }
    )
    if not final_review_result.get("ok"):
        final_vault_fields = _vault_result_fields(
            final_review_result,
            requested_default=import_vault_fields["requested_vault_dir"],
            effective_default=import_vault_fields["effective_vault_dir"],
            source_default=import_vault_fields["effective_vault_source"],
        )
        return {
            "ok": False,
            "error": final_review_result.get("error", "Failed to write final review note"),
            "topic": resolved_topic,
            "bundle_path": str(bundle_path),
            "review_input_path": review_input_path,
            "review_draft_path": review_draft_path,
            **final_vault_fields,
            "required_skills": final_review_result.get("required_skills", writing_input["required_skills"]),
            "read_skills": final_review_result.get("read_skills", writing_input["read_skills"]),
            "missing_required_skills": final_review_result.get("missing_required_skills", writing_input["missing_required_skills"]),
        }

    literature_note_paths = [
        str(row.get("relative_note_path", "")).strip()
        for row in (import_result.get("imported_notes") or [])
        if isinstance(row, dict) and str(row.get("relative_note_path", "")).strip()
    ]

    final_vault_fields = _vault_result_fields(
        final_review_result,
        requested_default=import_vault_fields["requested_vault_dir"],
        effective_default=import_vault_fields["effective_vault_dir"],
        source_default=import_vault_fields["effective_vault_source"],
    )

    return {
        "ok": True,
        "topic": resolved_topic,
        "category": resolved_category,
        "vault_dir": final_vault_fields["effective_vault_dir"],
        **final_vault_fields,
        "bundle_path": str(bundle_path),
        "review_note_path": str(final_review_result.get("note_path", final_review_result.get("relative_note_path", ""))).strip(),
        "review_input_path": review_input_path,
        "review_draft_path": review_draft_path,
        "literature_note_paths": literature_note_paths,
        "import_stats": {
            "processed_parent_items": int(import_result.get("processed_parent_items", 0) or 0),
            "imported_count": int(import_result.get("imported_count", 0) or 0),
            "skipped_count": int(import_result.get("skipped_count", 0) or 0),
        },
        "pdf_stats": pdf_stats,
        "warnings": warnings,
        "skill_pipeline": writing_input["skill_pipeline"],
        "required_skills": final_review_result.get("required_skills", writing_input["required_skills"]),
        "read_skills": final_review_result.get("read_skills", writing_input["read_skills"]),
        "missing_required_skills": final_review_result.get("missing_required_skills", writing_input["missing_required_skills"]),
        "generated_at": writing_input["generated_at"],
    }
