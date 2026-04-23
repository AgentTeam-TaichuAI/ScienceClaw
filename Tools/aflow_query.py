import json
import logging
import re
from typing import Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Database & API",
    "subcategory": "Materials Science",
    "tags": ["materials", "database", "aflow", "aflux", "band-gap", "formation-energy"],
    "library_target": "science",
}

_AFLOW_BASE_URL = "https://aflow.org/API/aflux/"
_DEFAULT_PROPERTIES = "compound,auid,aurl,spacegroup_relax,Pearson_symbol_relax,species,nspecies,enthalpy_formation_atom,Egap"
_DEFAULT_TIMEOUT = 30.0
_ELEMENT_RE = re.compile(r"^[A-Z][a-z]?$")
_PROPERTY_RE = re.compile(r"^[A-Za-z0-9_]+$")


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
                f"Invalid element symbol '{cleaned}'. Use comma-separated symbols like 'Mn,Pd' or 'Li,Fe,P,O'."
            )
        if normalized not in seen:
            seen.add(normalized)
            parsed.append(normalized)
    return parsed


def _parse_properties(properties: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for token in str(properties or "").split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        if not _PROPERTY_RE.match(cleaned):
            raise ValueError(
                f"Invalid AFLOW property '{cleaned}'. Use comma-separated identifiers like 'compound,auid,Egap'."
            )
        if cleaned not in seen:
            seen.add(cleaned)
            items.append(cleaned)
    return items


def _range_clause(keyword: str, minimum: Optional[float], maximum: Optional[float]) -> str:
    if minimum is None and maximum is None:
        return ""
    if minimum is not None and maximum is not None:
        return f"{keyword}({minimum}*,*{maximum})"
    if minimum is not None:
        return f"{keyword}({minimum}*)"
    return f"{keyword}(*{maximum})"


@tool
def aflow_query(
    elements: str = "",
    raw_matchbook: str = "",
    properties: str = _DEFAULT_PROPERTIES,
    limit: int = 10,
    page: int = 1,
    exact_species_match: bool = True,
    band_gap_min: Optional[float] = None,
    band_gap_max: Optional[float] = None,
    formation_enthalpy_min: Optional[float] = None,
    formation_enthalpy_max: Optional[float] = None,
) -> dict:
    """Query the AFLOW AFLUX API for materials entries and selected property columns.

    Use this tool when you need AFLOW materials data such as AFLOW IDs, compounds,
    formation enthalpy, band gap, relaxed space group, or Pearson symbol. It
    supports a simple element helper and also allows advanced AFLUX `raw_matchbook`
    clauses for expert queries.

    Args:
        elements: Optional comma-separated elements. Example: "Mn,Pd".
            This adds `species(Mn,Pd)` automatically.
        raw_matchbook: Optional advanced AFLUX clauses, for example:
            "Egap(1*,*2),Pearson_symbol_relax(*'c'*)". It is appended to the
            helper-generated clauses, so avoid duplicating the same filters.
        properties: Comma-separated AFLUX properties to include in the response.
            Example: "compound,auid,Egap,enthalpy_formation_atom".
        limit: Page size. Must be between 1 and 100.
        page: AFLUX page number. Use 1 for the first page.
        exact_species_match: If true and `elements` is provided, also adds
            `nspecies(<len(elements)>)` so results match exactly that species count.
        band_gap_min: Optional lower bound applied as `Egap(min*)`.
        band_gap_max: Optional upper bound applied as `Egap(*max)`.
        formation_enthalpy_min: Optional lower bound applied to `enthalpy_formation_atom`.
        formation_enthalpy_max: Optional upper bound applied to `enthalpy_formation_atom`.

    Returns:
        A dict with the resolved AFLUX query URL, query string, returned row count,
        and the parsed JSON result rows.
    """
    logger.info(
        "[aflow_query] elements=%r raw_matchbook=%r properties=%r limit=%s page=%s exact_species_match=%s band_gap_min=%r band_gap_max=%r formation_enthalpy_min=%r formation_enthalpy_max=%r",
        elements,
        raw_matchbook,
        properties,
        limit,
        page,
        exact_species_match,
        band_gap_min,
        band_gap_max,
        formation_enthalpy_min,
        formation_enthalpy_max,
    )

    if limit < 1 or limit > 100:
        return {"ok": False, "error": "limit must be between 1 and 100"}
    if page < 1:
        return {"ok": False, "error": "page must be >= 1"}

    try:
        parsed_elements = _parse_elements(elements)
        parsed_properties = _parse_properties(properties or _DEFAULT_PROPERTIES)
    except ValueError as exc:
        logger.error("[aflow_query] invalid input: %s", exc)
        return {"ok": False, "error": str(exc)}

    raw_lower = str(raw_matchbook or "").lower()
    clauses: list[str] = []
    if parsed_elements and "species(" not in raw_lower:
        clauses.append(f"species({','.join(parsed_elements)})")
    if parsed_elements and exact_species_match and "nspecies(" not in raw_lower:
        clauses.append(f"nspecies({len(parsed_elements)})")

    band_gap_clause = _range_clause("Egap", band_gap_min, band_gap_max)
    if band_gap_clause and "egap(" not in raw_lower:
        clauses.append(band_gap_clause)

    formation_clause = _range_clause(
        "enthalpy_formation_atom",
        formation_enthalpy_min,
        formation_enthalpy_max,
    )
    if formation_clause and "enthalpy_formation_atom(" not in raw_lower:
        clauses.append(formation_clause)

    cleaned_raw_matchbook = str(raw_matchbook or "").strip().strip(",")
    if cleaned_raw_matchbook:
        clauses.append(cleaned_raw_matchbook)

    clauses.extend(parsed_properties)
    clauses.append(f"$paging({page},{limit})")
    clauses.append("$format(json)")

    summon = ",".join(clauses)
    query_url = f"{_AFLOW_BASE_URL}?{summon}"

    try:
        response = httpx.get(query_url, timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("[aflow_query] HTTP error: %s", exc)
        detail = exc.response.text[:800] if exc.response is not None else str(exc)
        return {
            "ok": False,
            "error": f"AFLOW request failed with status {exc.response.status_code if exc.response is not None else 'unknown'}",
            "query_url": str(exc.request.url) if exc.request is not None else query_url,
            "detail": detail,
        }
    except Exception as exc:
        logger.error("[aflow_query] request failed: %s", exc)
        return {"ok": False, "error": f"AFLOW request failed: {exc}", "query_url": query_url}

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        logger.error("[aflow_query] invalid JSON: %s", exc)
        return {
            "ok": False,
            "error": f"AFLOW returned non-JSON response: {exc}",
            "query_url": str(response.url),
            "detail": response.text[:1000],
        }

    records = payload if isinstance(payload, list) else payload.get("data", [])
    result = {
        "ok": True,
        "database": "AFLOW",
        "query_url": str(response.url),
        "summon": summon,
        "returned": len(records) if isinstance(records, list) else 0,
        "data": records,
    }
    logger.info("[aflow_query] success returned=%s", result["returned"])
    return result
