"""
ToolUniverse REST API — 科研工具目录、规格查看与在线调试。

直接在后端进程内加载 ToolUniverse（无需 Sandbox Jupyter 代理），
通过内存缓存提供高性能的工具列表与规格查询。
支持 lang 参数返回中文翻译版本。
"""
from __future__ import annotations

import inspect
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from backend.route.sessions import (
    _TOOLS_DIR as _SESSIONS_TOOLS_DIR,
    _external_proxy_map,
    _normalize_external_result,
    _parse_external_tool_file,
    _tool_schema_json,
    _validate_external_arguments,
)
from backend.tool_library_taxonomy import DISCIPLINE_LABELS, classify_science_tool
from backend.user.dependencies import require_user, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tooluniverse", tags=["tooluniverse"])

# ── ToolUniverse 单例 ──────────────────────────────────────────────

_tu = None
_tu_loading = False
_TOOLS_DIR = Path(_SESSIONS_TOOLS_DIR)
_SCIENCE_LIBRARY_TARGET = "science"


def _get_tu():
    global _tu, _tu_loading
    if _tu is not None:
        return _tu
    if _tu_loading:
        return None
    _tu_loading = True
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        _tu = tu
        logger.info(f"[TU-API] ToolUniverse loaded: {len(tu.all_tools)} tools")
        return _tu
    except Exception as exc:
        logger.error(f"[TU-API] Failed to load ToolUniverse: {exc}")
        _tu_loading = False
        return None


def _science_overlay_taxonomy(name: str, category: str, subcategory: str, description: str) -> Dict[str, Any]:
    return classify_science_tool(
        name=name,
        raw_category=category,
        description=" ".join(part for part in [subcategory, description] if part),
        tool_type=subcategory or "local_proxy",
    )


def _build_science_overlay_spec(py_file: Path, meta: Dict[str, Any], proxy: Any) -> Dict[str, Any]:
    schema = _tool_schema_json(proxy)
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []
    taxonomy = _science_overlay_taxonomy(
        name=py_file.stem,
        category=str(meta.get("category", "")),
        subcategory=str(meta.get("subcategory", "")),
        description=str(meta.get("description", "")),
    )
    return {
        "name": py_file.stem,
        "description": str(meta.get("description", "")),
        "parameters": schema,
        "test_examples": [],
        "return_schema": None,
        "category": str(meta.get("category", "")),
        "tool_type": str(meta.get("subcategory", "")) or "local_proxy",
        "family": _derive_tool_family(py_file.stem),
        "action": _derive_tool_action(py_file.stem),
        "source_file": str(py_file),
        "runner": "structured_proxy",
        "param_count": len(props) if isinstance(props, dict) else 0,
        "required_params": required if isinstance(required, list) else [],
        "has_examples": False,
        "has_return_schema": False,
        **taxonomy,
    }


def _list_science_overlay_tools(force_reload: bool = False) -> List[Dict[str, Any]]:
    if not _TOOLS_DIR.is_dir():
        return []

    proxies = _external_proxy_map(force_reload=force_reload)
    overlay_tools: List[Dict[str, Any]] = []

    for py_file in sorted(_TOOLS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        meta = _parse_external_tool_file(py_file)
        if meta.get("library_target") != _SCIENCE_LIBRARY_TARGET:
            continue

        proxy = proxies.get(meta.get("tool_name") or py_file.stem) or proxies.get(py_file.stem)
        if proxy is None:
            logger.warning("[TU-API] Science overlay tool missing proxy: %s", py_file.stem)
            continue

        spec = _build_science_overlay_spec(py_file, meta, proxy)
        overlay_tools.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "category": spec["category"],
                "tool_type": spec["tool_type"],
                "family": spec["family"],
                "action": spec["action"],
                "function_group": spec["function_group"],
                "function_group_zh": spec["function_group_zh"],
                "discipline": spec["discipline"],
                "discipline_zh": spec["discipline_zh"],
                "system_group": spec["system_group"],
                "system_group_zh": spec["system_group_zh"],
                "system_subgroup": spec["system_subgroup"],
                "system_subgroup_zh": spec["system_subgroup_zh"],
                "param_count": spec["param_count"],
                "required_params": spec["required_params"],
                "has_examples": spec["has_examples"],
                "has_return_schema": spec["has_return_schema"],
                "source_file": spec["source_file"],
                "runner": spec["runner"],
            }
        )

    return overlay_tools


def _science_overlay_spec_map(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    if not _TOOLS_DIR.is_dir():
        return {}

    proxies = _external_proxy_map(force_reload=force_reload)
    result: Dict[str, Dict[str, Any]] = {}

    for py_file in sorted(_TOOLS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        meta = _parse_external_tool_file(py_file)
        if meta.get("library_target") != _SCIENCE_LIBRARY_TARGET:
            continue

        proxy = proxies.get(meta.get("tool_name") or py_file.stem) or proxies.get(py_file.stem)
        if proxy is None:
            continue

        spec = _build_science_overlay_spec(py_file, meta, proxy)
        spec["_proxy"] = proxy
        result[spec["name"]] = spec

    return result


# ── 翻译文件加载 ──────────────────────────────────────────────────

_TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"
_translations: Dict[str, Dict[str, Any]] = {}


def _load_translations():
    """加载翻译文件到内存（启动时调用一次）。"""
    global _translations
    zh_file = _TRANSLATIONS_DIR / "tu_zh.json"
    if zh_file.exists():
        try:
            data = json.loads(zh_file.read_text(encoding="utf-8"))
            _translations["zh"] = data
            tool_count = len(data.get("tools", {}))
            cat_count = len(data.get("categories", {}))
            logger.info(f"[TU-API] Loaded zh translations: {tool_count} tools, {cat_count} categories")
        except Exception as exc:
            logger.warning(f"[TU-API] Failed to load zh translations: {exc}")


_load_translations()


def _get_translation(lang: str) -> Optional[Dict[str, Any]]:
    if lang and lang != "en":
        return _translations.get(lang)
    return None


def _translate_tool_list_item(item: Dict, trans: Dict[str, Any]) -> Dict:
    """Apply translation to a tool list item."""
    tools_tr = trans.get("tools", {})
    cats_tr = trans.get("categories", {})

    name = item.get("name", "")
    tool_tr = tools_tr.get(name)
    result = dict(item)
    if tool_tr:
        if tool_tr.get("description"):
            result["description"] = tool_tr["description"]
    cat = item.get("category", "")
    if cat and cat in cats_tr:
        result["category_zh"] = cats_tr[cat]
    return result


def _translate_tool_spec(spec: Dict, trans: Dict[str, Any]) -> Dict:
    """Apply translation to a tool spec (detail page)."""
    tools_tr = trans.get("tools", {})
    cats_tr = trans.get("categories", {})

    name = spec.get("name", "")
    tool_tr = tools_tr.get(name, {})
    result = dict(spec)

    if tool_tr.get("description"):
        result["description"] = tool_tr["description"]

    params_tr = tool_tr.get("params", {})
    if params_tr and result.get("parameters", {}).get("properties"):
        props = dict(result["parameters"]["properties"])
        for pname, pinfo in props.items():
            if pname in params_tr:
                props[pname] = {**pinfo, "description": params_tr[pname]}
        result["parameters"] = {**result["parameters"], "properties": props}

    cat = spec.get("category", "")
    if cat and cat in cats_tr:
        result["category_zh"] = cats_tr[cat]
    return result


# ── 缓存 ──────────────────────────────────────────────────────────

_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL = 600


def _get_cached(key: str):
    if key in _cache and (time.time() - _cache_ts.get(key, 0)) < _CACHE_TTL:
        return _cache[key]
    return None


def _set_cached(key: str, value: Any):
    _cache[key] = value
    _cache_ts[key] = time.time()


# ── 辅助 ──────────────────────────────────────────────────────────

_CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def _sanitize(text: str) -> str:
    return _CTRL_RE.sub('', text) if text else ""


def _derive_tool_family(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    for delimiter in ("_", "-"):
        if delimiter in raw:
            prefix = raw.split(delimiter, 1)[0].strip()
            if prefix:
                return prefix
    return raw


def _derive_tool_action(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    for delimiter in ("_", "-"):
        parts = [part.strip() for part in raw.split(delimiter) if part.strip()]
        if len(parts) >= 2:
            return parts[1]
    return ""


def _build_tools_list(tu) -> List[Dict]:
    tools = []
    items = tu.all_tools
    if isinstance(items, dict):
        items = list(items.values())

    for tool in items:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name", "")
        if not name:
            continue

        desc = tool.get("description", "")
        tool_type = tool.get("type", "") or ""
        category = tool.get("category", "") or tool_type
        params = tool.get("parameter", tool.get("parameters", {}))
        param_count = 0
        required_params: List[str] = []
        if isinstance(params, dict):
            props = params.get("properties", {})
            param_count = len(props) if isinstance(props, dict) else 0
            req = params.get("required", [])
            if isinstance(req, list):
                required_params = req

        examples = tool.get("test_examples", [])
        has_return = bool(tool.get("return_schema"))
        taxonomy = classify_science_tool(
            name=name,
            raw_category=category,
            description=desc,
            tool_type=tool_type,
        )

        tools.append({
            "name": name,
            "description": _sanitize(desc),
            "category": category,
            "tool_type": tool_type,
            "family": _derive_tool_family(name),
            "action": _derive_tool_action(name),
            "function_group": taxonomy["function_group"],
            "function_group_zh": taxonomy["function_group_zh"],
            "discipline": taxonomy["discipline"],
            "discipline_zh": taxonomy["discipline_zh"],
            "system_group": taxonomy["system_group"],
            "system_group_zh": taxonomy["system_group_zh"],
            "system_subgroup": taxonomy["system_subgroup"],
            "system_subgroup_zh": taxonomy["system_subgroup_zh"],
            "param_count": param_count,
            "required_params": required_params,
            "has_examples": len(examples) > 0,
            "has_return_schema": has_return,
        })
    return tools


# ── API 端点 ──────────────────────────────────────────────────────

class ToolRunRequest(BaseModel):
    arguments: Dict[str, Any]


@router.get("/tools")
async def list_tools(
    search: str = Query(default="", description="搜索关键词"),
    category: str = Query(default="", description="按类别过滤"),
    lang: str = Query(default="en", description="语言: en / zh"),
    _user: User = Depends(require_user),
):
    """列出所有 ToolUniverse 工具。"""
    cache_key = "tu_tools_list_v3"
    cached = _get_cached(cache_key)

    if cached is None:
        tu = _get_tu()
        cached = _build_tools_list(tu) if tu is not None else []
        cached.extend(_list_science_overlay_tools(force_reload=True))
        if not cached:
            raise HTTPException(status_code=503, detail="ToolUniverse is loading, please retry in a moment")
        _set_cached(cache_key, cached)

    trans = _get_translation(lang)
    tools = cached
    if trans:
        tools = [_translate_tool_list_item(t, trans) for t in tools]

    if search:
        q = search.lower()
        if trans:
            tools = [t for t in tools if q in t["name"].lower()
                     or q in t.get("description", "").lower()
                     or q in t.get("family", "").lower()
                     or q in t.get("action", "").lower()
                     or q in t.get("tool_type", "").lower()
                     or q in t.get("function_group", "").lower()
                     or q in t.get("discipline", "").lower()
                     or q in t.get("system_group", "").lower()
                     or q in t.get("system_subgroup", "").lower()
                     or q in t.get("function_group_zh", "").lower()
                     or q in t.get("discipline_zh", "").lower()
                     or q in t.get("system_group_zh", "").lower()
                     or q in t.get("system_subgroup_zh", "").lower()
                     or q in next((c["description"] for c in cached if c["name"] == t["name"]), "").lower()]
        else:
            tools = [t for t in tools if q in t["name"].lower()
                     or q in t.get("description", "").lower()
                     or q in t.get("family", "").lower()
                     or q in t.get("action", "").lower()
                     or q in t.get("tool_type", "").lower()
                     or q in t.get("function_group", "").lower()
                     or q in t.get("discipline", "").lower()
                     or q in t.get("system_group", "").lower()
                     or q in t.get("system_subgroup", "").lower()
                     or q in t.get("function_group_zh", "").lower()
                     or q in t.get("discipline_zh", "").lower()
                     or q in t.get("system_group_zh", "").lower()
                     or q in t.get("system_subgroup_zh", "").lower()]
    if category:
        tools = [t for t in tools if t.get("category", "").lower() == category.lower()]

    categories = sorted(set(t.get("category", "") for t in cached if t.get("category")))
    return {"tools": tools, "total": len(cached), "categories": categories}


@router.get("/tools/{tool_name}")
async def get_tool_spec(
    tool_name: str,
    lang: str = Query(default="en", description="语言: en / zh"),
    _user: User = Depends(require_user),
):
    """获取单个工具的详细规格。"""
    overlay_spec = _science_overlay_spec_map(force_reload=False).get(tool_name)
    if overlay_spec is not None:
        cleaned = dict(overlay_spec)
        cleaned.pop("_proxy", None)
        trans = _get_translation(lang)
        if trans:
            return _translate_tool_spec(cleaned, trans)
        return cleaned

    cache_key = f"tu_spec_v2_{tool_name}"
    cached = _get_cached(cache_key)
    if not cached:
        tu = _get_tu()
        if tu is None:
            raise HTTPException(status_code=503, detail="ToolUniverse is loading")

        try:
            spec = tu.tool_specification(tool_name, format="openai")
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}") from exc

        if not spec:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

        raw_tool = None
        for t in (tu.all_tools if isinstance(tu.all_tools, list) else tu.all_tools.values()):
            if isinstance(t, dict) and t.get("name") == tool_name:
                raw_tool = t
                break

        cached = {
            **spec,
            "test_examples": [],
            "return_schema": None,
            "category": "",
            "tool_type": "",
            "family": "",
            "action": "",
            "function_group": "",
            "function_group_zh": "",
            "discipline": "",
            "discipline_zh": "",
            "system_group": "",
            "system_group_zh": "",
            "system_subgroup": "",
            "system_subgroup_zh": "",
            "source_file": "",
        }
        if raw_tool:
            raw_tool_type = raw_tool.get("type", "") or ""
            raw_category = raw_tool.get("category", "") or raw_tool_type
            taxonomy = classify_science_tool(
                name=tool_name,
                raw_category=raw_category,
                description=cached.get("description", ""),
                tool_type=raw_tool_type,
            )
            cached["test_examples"] = raw_tool.get("test_examples", [])
            cached["return_schema"] = raw_tool.get("return_schema")
            cached["tool_type"] = raw_tool_type
            cached["category"] = raw_category
            cached["family"] = _derive_tool_family(tool_name)
            cached["action"] = _derive_tool_action(tool_name)
            cached["function_group"] = taxonomy["function_group"]
            cached["function_group_zh"] = taxonomy["function_group_zh"]
            cached["discipline"] = taxonomy["discipline"]
            cached["discipline_zh"] = taxonomy["discipline_zh"]
            cached["system_group"] = taxonomy["system_group"]
            cached["system_group_zh"] = taxonomy["system_group_zh"]
            cached["system_subgroup"] = taxonomy["system_subgroup"]
            cached["system_subgroup_zh"] = taxonomy["system_subgroup_zh"]
            cached["source_file"] = raw_tool.get("source_file", "")
            cached["description"] = _sanitize(cached.get("description", ""))

        _set_cached(cache_key, cached)

    trans = _get_translation(lang)
    if trans:
        return _translate_tool_spec(cached, trans)
    return cached


@router.post("/tools/{tool_name}/run")
async def run_tool(
    tool_name: str,
    body: ToolRunRequest,
    _user: User = Depends(require_user),
):
    try:
        overlay_spec = _science_overlay_spec_map(force_reload=True).get(tool_name)
        if overlay_spec is not None:
            proxy = overlay_spec["_proxy"]
            arguments = _validate_external_arguments(proxy, body.arguments)
            runner = getattr(proxy, "coroutine", None) or getattr(proxy, "func", None)
            if runner is None:
                raise RuntimeError(f"Tool '{tool_name}' is missing an executable runner")

            result = runner(**arguments)
            if inspect.isawaitable(result):
                result = await result
            return _normalize_external_result(result)

        tu = _get_tu()
        if tu is None:
            raise HTTPException(status_code=503, detail="ToolUniverse is loading")

        result = tu.run({"name": tool_name, "arguments": body.arguments})
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        logger.error(f"[TU-API] Tool execution failed: {tool_name} - {exc}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {exc}") from exc

    return {"success": True, "result": result}


@router.get("/categories")
async def list_categories(
    lang: str = Query(default="en", description="语言: en / zh"),
    _user: User = Depends(require_user),
):
    cache_key = "tu_tools_list_v3"
    cached = _get_cached(cache_key)
    if cached is None:
        tu = _get_tu()
        cached = _build_tools_list(tu) if tu is not None else []
        cached.extend(_list_science_overlay_tools(force_reload=True))
        if not cached:
            raise HTTPException(status_code=503, detail="ToolUniverse is loading")
        _set_cached(cache_key, cached)

    trans = _get_translation(lang)
    cats_tr = trans.get("categories", {}) if trans else {}

    counts: Dict[str, int] = {}
    for t in cached:
        cat = t.get("discipline", "general_compute") or "general_compute"
        counts[cat] = counts.get(cat, 0) + 1

    return {
        "categories": [
            {"name": k, "name_zh": DISCIPLINE_LABELS.get(k, cats_tr.get(k, "")), "count": v}
            for k, v in sorted(counts.items())
        ]
    }
