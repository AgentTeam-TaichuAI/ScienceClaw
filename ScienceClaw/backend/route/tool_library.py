from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.tool_library_preferences import (
    BatchAssignToolLibraryRequest,
    ClearToolLibraryAssignmentsRequest,
    UpdateToolLibraryPreferencesRequest,
    get_tool_library_preferences,
    update_tool_library_preferences,
    batch_assign_tool_library,
    clear_tool_library_assignments,
)
from backend.user.dependencies import User, require_user


router = APIRouter(prefix="/tool-library", tags=["tool-library"])


class ApiResponse(BaseModel):
    code: int = Field(default=0)
    msg: str = Field(default="ok")
    data: Any = Field(default=None)


@router.get("/preferences", response_model=ApiResponse)
async def get_preferences(current_user: User = Depends(require_user)) -> ApiResponse:
    prefs = await get_tool_library_preferences(current_user.id)
    return ApiResponse(data=prefs.model_dump())


@router.put("/preferences", response_model=ApiResponse)
async def update_preferences(
    body: UpdateToolLibraryPreferencesRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    try:
        prefs = await update_tool_library_preferences(current_user.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=prefs.model_dump())


@router.post("/assignments/batch", response_model=ApiResponse)
async def batch_assignments(
    body: BatchAssignToolLibraryRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    try:
        prefs = await batch_assign_tool_library(current_user.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=prefs.model_dump())


@router.delete("/assignments", response_model=ApiResponse)
async def clear_assignments(
    body: ClearToolLibraryAssignmentsRequest = Body(...),
    current_user: User = Depends(require_user),
) -> ApiResponse:
    prefs = await clear_tool_library_assignments(current_user.id, body)
    return ApiResponse(data=prefs.model_dump())

