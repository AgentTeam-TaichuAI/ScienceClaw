from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Iterable, List

from backend.tool_library_taxonomy import find_boundary_mismatch_phrases


def _counter_to_rows(counter: Counter[str]) -> List[Dict[str, Any]]:
    return [
        {"id": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def audit_tool_payloads(items: Iterable[Dict[str, Any]], *, tool_kind: str) -> Dict[str, Any]:
    rows = list(items)
    discipline_counts: Counter[str] = Counter()
    function_group_counts: Counter[str] = Counter()
    suspicious: List[Dict[str, Any]] = []

    for item in rows:
        discipline = str(item.get("discipline") or item.get("system_subgroup") or "")
        function_group = str(item.get("function_group") or item.get("system_group") or "")
        if discipline:
            discipline_counts[discipline] += 1
        if function_group:
            function_group_counts[function_group] += 1

        mismatches = find_boundary_mismatch_phrases(
            item.get("name", ""),
            item.get("category", ""),
            item.get("subcategory", ""),
            item.get("tool_type", ""),
            item.get("description", ""),
            item.get("tags", []),
        )
        if mismatches:
            suspicious.append(
                {
                    "name": item.get("name", ""),
                    "tool_kind": tool_kind,
                    "mismatches": mismatches,
                }
            )

    return {
        "tool_kind": tool_kind,
        "total": len(rows),
        "discipline_counts": _counter_to_rows(discipline_counts),
        "function_group_counts": _counter_to_rows(function_group_counts),
        "suspicious_boundary_mismatch_count": len(suspicious),
        "suspicious_boundary_mismatches": suspicious,
    }


def audit_loaded_tool_library() -> Dict[str, Any]:
    from backend.route.sessions import _list_external_tools
    from backend.route.tooluniverse import _build_tools_list, _get_tu

    tu = _get_tu()
    science_tools = _build_tools_list(tu) if tu is not None else []
    external_tools = _list_external_tools(force_reload=True)

    return {
        "science": audit_tool_payloads(science_tools, tool_kind="science"),
        "external": audit_tool_payloads(external_tools, tool_kind="external"),
    }


if __name__ == "__main__":
    print(json.dumps(audit_loaded_tool_library(), ensure_ascii=False, indent=2))
