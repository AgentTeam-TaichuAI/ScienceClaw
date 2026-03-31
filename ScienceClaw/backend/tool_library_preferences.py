from __future__ import annotations

from typing import Dict, List, Literal, Tuple

from pydantic import BaseModel, Field

from backend.mongodb.db import db


ToolKind = Literal["science", "external"]


def _normalize_whitespace(value: str) -> str:
    return " ".join(str(value or "").split())


def _name_key(value: str) -> str:
    return _normalize_whitespace(value).casefold()


class ToolLibrarySubcategory(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    order: int = Field(default=0)


class ToolLibraryCategory(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    order: int = Field(default=0)
    subcategories: List[ToolLibrarySubcategory] = Field(default_factory=list)


class ToolLibraryAssignment(BaseModel):
    tool_kind: ToolKind
    tool_name: str = Field(..., min_length=1, max_length=255)
    category_id: str = Field(..., min_length=1, max_length=120)
    subcategory_id: str = Field(default="", max_length=120)


class ToolLibraryPreferences(BaseModel):
    custom_categories: List[ToolLibraryCategory] = Field(default_factory=list)
    assignments: List[ToolLibraryAssignment] = Field(default_factory=list)


class UpdateToolLibraryPreferencesRequest(BaseModel):
    custom_categories: List[ToolLibraryCategory] = Field(default_factory=list)


class BatchAssignToolLibraryRequest(BaseModel):
    tool_kind: ToolKind
    tool_names: List[str] = Field(default_factory=list)
    category_id: str = Field(..., min_length=1, max_length=120)
    subcategory_id: str = Field(default="", max_length=120)


class ClearToolLibraryAssignmentsRequest(BaseModel):
    tool_kind: ToolKind
    tool_names: List[str] = Field(default_factory=list)


def _sort_categories(categories: List[ToolLibraryCategory]) -> List[ToolLibraryCategory]:
    sorted_categories: List[ToolLibraryCategory] = []
    for category in sorted(categories, key=lambda item: (item.order, _name_key(item.name), item.id)):
        subcategories = sorted(
            category.subcategories,
            key=lambda item: (item.order, _name_key(item.name), item.id),
        )
        sorted_categories.append(category.model_copy(update={"subcategories": subcategories}))
    return sorted_categories


def _normalize_preferences(doc: dict | None) -> ToolLibraryPreferences:
    if not doc:
        return ToolLibraryPreferences()
    doc = dict(doc)
    doc.pop("_id", None)
    prefs = ToolLibraryPreferences(**doc)
    categories, allowed_pairs = _validate_category_tree(prefs.custom_categories)
    assignments = _prune_assignments(prefs.assignments, allowed_pairs)
    return ToolLibraryPreferences(
        custom_categories=_sort_categories(categories),
        assignments=_sort_assignments(assignments),
    )


def _validate_category_tree(categories: List[ToolLibraryCategory]) -> Tuple[List[ToolLibraryCategory], Dict[str, set[str]]]:
    seen_category_ids: set[str] = set()
    seen_category_names: set[str] = set()
    normalized_categories: List[ToolLibraryCategory] = []
    allowed_pairs: Dict[str, set[str]] = {}

    for raw_category in categories:
        category = raw_category.model_copy(
            update={
                "id": raw_category.id.strip(),
                "name": _normalize_whitespace(raw_category.name),
            }
        )
        if not category.id or not category.name:
            continue
        if category.id in seen_category_ids:
            raise ValueError(f"Duplicate category id: {category.id}")
        seen_category_ids.add(category.id)
        category_name_key = _name_key(category.name)
        if category_name_key in seen_category_names:
            raise ValueError(f"Duplicate category name: {category.name}")
        seen_category_names.add(category_name_key)

        seen_sub_ids: set[str] = set()
        seen_sub_names: set[str] = set()
        normalized_subcategories: List[ToolLibrarySubcategory] = []
        allowed_pairs[category.id] = set()
        for raw_sub in category.subcategories:
            subcategory = raw_sub.model_copy(
                update={
                    "id": raw_sub.id.strip(),
                    "name": _normalize_whitespace(raw_sub.name),
                }
            )
            if not subcategory.id or not subcategory.name:
                continue
            if subcategory.id in seen_sub_ids:
                raise ValueError(f"Duplicate subcategory id: {subcategory.id}")
            seen_sub_ids.add(subcategory.id)
            subcategory_name_key = _name_key(subcategory.name)
            if subcategory_name_key in seen_sub_names:
                raise ValueError(
                    f'Duplicate subcategory name "{subcategory.name}" under "{category.name}"'
                )
            seen_sub_names.add(subcategory_name_key)
            normalized_subcategories.append(subcategory)
            allowed_pairs[category.id].add(subcategory.id)

        normalized_categories.append(
            category.model_copy(update={"subcategories": normalized_subcategories})
        )

    return normalized_categories, allowed_pairs


def _prune_assignments(
    assignments: List[ToolLibraryAssignment],
    allowed_pairs: Dict[str, set[str]],
) -> List[ToolLibraryAssignment]:
    normalized: List[ToolLibraryAssignment] = []
    seen_keys: set[tuple[str, str]] = set()
    for raw_assignment in assignments:
        assignment = raw_assignment.model_copy(
            update={
                "tool_name": _normalize_whitespace(raw_assignment.tool_name),
                "category_id": raw_assignment.category_id.strip(),
                "subcategory_id": raw_assignment.subcategory_id.strip(),
            }
        )
        if not assignment.tool_name or not assignment.category_id:
            continue
        if assignment.category_id not in allowed_pairs:
            continue
        if assignment.subcategory_id and assignment.subcategory_id not in allowed_pairs[assignment.category_id]:
            continue
        key = (assignment.tool_kind, assignment.tool_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        normalized.append(assignment)
    return normalized


def _sort_assignments(assignments: List[ToolLibraryAssignment]) -> List[ToolLibraryAssignment]:
    return sorted(assignments, key=lambda item: (item.tool_kind, _name_key(item.tool_name)))


async def get_tool_library_preferences(user_id: str) -> ToolLibraryPreferences:
    doc = await db.get_collection("tool_library_preferences").find_one({"_id": user_id})
    return _normalize_preferences(doc)


async def update_tool_library_preferences(
    user_id: str,
    updates: UpdateToolLibraryPreferencesRequest,
) -> ToolLibraryPreferences:
    current = await get_tool_library_preferences(user_id)
    categories, allowed_pairs = _validate_category_tree(updates.custom_categories)
    assignments = _prune_assignments(current.assignments, allowed_pairs)
    prefs = ToolLibraryPreferences(
        custom_categories=_sort_categories(categories),
        assignments=_sort_assignments(assignments),
    )
    await db.get_collection("tool_library_preferences").update_one(
        {"_id": user_id},
        {"$set": prefs.model_dump()},
        upsert=True,
    )
    return prefs


async def batch_assign_tool_library(
    user_id: str,
    request: BatchAssignToolLibraryRequest,
) -> ToolLibraryPreferences:
    current = await get_tool_library_preferences(user_id)
    _, allowed_pairs = _validate_category_tree(current.custom_categories)
    if request.category_id not in allowed_pairs:
        raise ValueError(f"Unknown category id: {request.category_id}")
    if request.subcategory_id and request.subcategory_id not in allowed_pairs[request.category_id]:
        raise ValueError(f"Unknown subcategory id: {request.subcategory_id}")

    unique_tool_names = [
        _normalize_whitespace(name)
        for name in request.tool_names
        if isinstance(name, str) and _normalize_whitespace(name)
    ]
    next_assignments: Dict[tuple[str, str], ToolLibraryAssignment] = {
        (assignment.tool_kind, assignment.tool_name): assignment
        for assignment in current.assignments
    }
    for tool_name in unique_tool_names:
        assignment = ToolLibraryAssignment(
            tool_kind=request.tool_kind,
            tool_name=tool_name,
            category_id=request.category_id,
            subcategory_id=request.subcategory_id.strip(),
        )
        next_assignments[(request.tool_kind, tool_name)] = assignment

    prefs = ToolLibraryPreferences(
        custom_categories=current.custom_categories,
        assignments=_sort_assignments(list(next_assignments.values())),
    )
    await db.get_collection("tool_library_preferences").update_one(
        {"_id": user_id},
        {"$set": prefs.model_dump()},
        upsert=True,
    )
    return prefs


async def clear_tool_library_assignments(
    user_id: str,
    request: ClearToolLibraryAssignmentsRequest,
) -> ToolLibraryPreferences:
    current = await get_tool_library_preferences(user_id)
    targets = {
        (request.tool_kind, _normalize_whitespace(name))
        for name in request.tool_names
        if isinstance(name, str) and _normalize_whitespace(name)
    }
    assignments = [
        assignment
        for assignment in current.assignments
        if (assignment.tool_kind, assignment.tool_name) not in targets
    ]
    prefs = ToolLibraryPreferences(
        custom_categories=current.custom_categories,
        assignments=_sort_assignments(assignments),
    )
    await db.get_collection("tool_library_preferences").update_one(
        {"_id": user_id},
        {"$set": prefs.model_dump()},
        upsert=True,
    )
    return prefs
