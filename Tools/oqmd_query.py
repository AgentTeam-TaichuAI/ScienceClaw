import logging
import re
from typing import Any, Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Database & API",
    "subcategory": "Materials Science",
    "tags": ["materials", "database", "oqmd", "phase-stability", "formation-energy"],
    "library_target": "science",
}

_OQMD_BASE_URL = "https://oqmd.org/oqmdapi"
_DEFAULT_RESOURCE = "formationenergy"
_DEFAULT_FIELDS = "name,entry_id,delta_e,stability,band_gap,spacegroup,prototype"
_DEFAULT_TIMEOUT = 30.0
_ELEMENT_RE = re.compile(r"^[A-Z][a-z]?$")
_RESOURCE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _parse_elements(elements: str) -> list[str]:
    seen: set[str] = set()
    parsed: list[str] = []
    for token in re.split(r"[\s,;|/\-]+", str(elements or "").strip()):
        cleaned = token.strip()
        if not cleaned:
            continue
        normalized = cleaned[0].upper() + cleaned[1:].lower()
        if not _ELEMENT_RE.match(normalized):
            raise ValueError(
                f"Invalid element symbol '{cleaned}'. Use comma-separated symbols like 'Fe,O' or 'Li,Fe,P,O'."
            )
        if normalized not in seen:
            seen.add(normalized)
            parsed.append(normalized)
    return parsed


def _clean_csv_list(raw_value: str, *, fallback: str) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for token in str(raw_value or "").split(","):
        cleaned = token.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        items.append(cleaned)
    return ",".join(items) if items else fallback


def _float_clause(field: str, minimum: Optional[float], maximum: Optional[float]) -> list[str]:
    clauses: list[str] = []
    if minimum is not None:
        clauses.append(f"{field}>={minimum}")
    if maximum is not None:
        clauses.append(f"{field}<={maximum}")
    return clauses


@tool
def oqmd_query(
    elements: str = "",
    raw_filter: str = "",
    fields: str = _DEFAULT_FIELDS,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "",
    stability_max: Optional[float] = None,
    band_gap_min: Optional[float] = None,
    band_gap_max: Optional[float] = None,
    resource: str = _DEFAULT_RESOURCE,
) -> dict:
    """Query the OQMD materials database for entries, energies, and stability metadata.

    Use this tool when you need real OQMD data for inorganic compounds, such as
    formation energy, stability above hull, band gap, prototype, or space group.
    It supports a simple element-based query helper and also accepts an advanced
    OQMD/OPTIMADE-style `raw_filter` for precise searches.

    Args:
        elements: Optional comma-separated element symbols. Example: "Fe,O" or "Li,Fe,P,O".
            When provided, the tool adds `element_set=(...)` to the OQMD filter.
        raw_filter: Optional advanced OQMD filter expression. Example:
            "element_set=(Fe,O) AND stability<=0.05". This is appended with AND
            to any helper filters built from other parameters.
        fields: Comma-separated OQMD fields to return. Example:
            "name,entry_id,delta_e,stability,band_gap,spacegroup,prototype".
        limit: Maximum number of rows to return. Must be between 1 and 100.
        offset: Pagination offset. Use 0 for the first page, 10 for the next page, etc.
        sort_by: Optional OQMD sort field, such as "stability" or "-stability".
        stability_max: Optional upper bound on OQMD `stability`.
        band_gap_min: Optional lower bound on OQMD `band_gap`.
        band_gap_max: Optional upper bound on OQMD `band_gap`.
        resource: OQMD API resource name. Defaults to "formationenergy".

    Returns:
        A dict with the resolved query URL, applied filter, returned row count,
        total available rows reported by OQMD, and the result records.
    """
    logger.info(
        "[oqmd_query] elements=%r raw_filter=%r fields=%r limit=%s offset=%s sort_by=%r stability_max=%r band_gap_min=%r band_gap_max=%r resource=%r",
        elements,
        raw_filter,
        fields,
        limit,
        offset,
        sort_by,
        stability_max,
        band_gap_min,
        band_gap_max,
        resource,
    )

    if limit < 1 or limit > 100:
        return {"ok": False, "error": "limit must be between 1 and 100"}
    if offset < 0:
        return {"ok": False, "error": "offset must be >= 0"}

    cleaned_resource = str(resource or "").strip() or _DEFAULT_RESOURCE
    if not _RESOURCE_RE.match(cleaned_resource):
        return {"ok": False, "error": f"Unsupported resource '{resource}'"}

    try:
        parsed_elements = _parse_elements(elements)
    except ValueError as exc:
        logger.error("[oqmd_query] invalid elements: %s", exc)
        return {"ok": False, "error": str(exc)}

    filter_clauses: list[str] = []
    if parsed_elements:
        filter_clauses.append(f"element_set=({','.join(parsed_elements)})")
    filter_clauses.extend(_float_clause("stability", None, stability_max))
    filter_clauses.extend(_float_clause("band_gap", band_gap_min, band_gap_max))

    cleaned_raw_filter = str(raw_filter or "").strip()
    if cleaned_raw_filter:
        filter_clauses.append(cleaned_raw_filter)

    params: dict[str, Any] = {
        "fields": _clean_csv_list(fields, fallback=_DEFAULT_FIELDS),
        "limit": limit,
        "offset": offset,
    }
    if filter_clauses:
        params["filter"] = " AND ".join(filter_clauses)
    if str(sort_by or "").strip():
        params["sort_by"] = str(sort_by).strip()

    url = f"{_OQMD_BASE_URL}/{cleaned_resource}"
    try:
        response = httpx.get(url, params=params, timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("[oqmd_query] HTTP error: %s", exc)
        detail = exc.response.text[:800] if exc.response is not None else str(exc)
        return {
            "ok": False,
            "error": f"OQMD request failed with status {exc.response.status_code if exc.response is not None else 'unknown'}",
            "query_url": str(exc.request.url) if exc.request is not None else url,
            "detail": detail,
        }
    except Exception as exc:
        logger.error("[oqmd_query] request failed: %s", exc)
        return {"ok": False, "error": f"OQMD request failed: {exc}", "query_url": url}

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("[oqmd_query] invalid JSON: %s", exc)
        return {
            "ok": False,
            "error": f"OQMD returned non-JSON response: {exc}",
            "query_url": str(response.url),
            "detail": response.text[:1000],
        }

    records = payload.get("data", [])
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    result = {
        "ok": True,
        "database": "OQMD",
        "resource": cleaned_resource,
        "query_url": str(response.url),
        "applied_filter": params.get("filter", ""),
        "fields": params["fields"],
        "returned": len(records) if isinstance(records, list) else 0,
        "available": meta.get("data_available"),
        "more_data_available": meta.get("more_data_available"),
        "timestamp": meta.get("time_stamp"),
        "data": records,
    }
    logger.info(
        "[oqmd_query] success resource=%s returned=%s available=%s",
        cleaned_resource,
        result["returned"],
        result["available"],
    )
    return result
