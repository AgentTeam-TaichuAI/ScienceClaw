from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.desktop_bridge import request_desktop_bridge
from backend.user.dependencies import require_user, User

router = APIRouter(prefix="/desktop", tags=["desktop"])


class ApiResponse(BaseModel):
    code: int = Field(default=0)
    msg: str = Field(default="ok")
    data: Any = Field(default=None)


class PickDirectoryRequest(BaseModel):
    title: str = Field(default="Select Obsidian vault")
    initial_dir: str = Field(default="")


class EnsureVaultRequest(BaseModel):
    vault_dir: str = Field(min_length=1, max_length=1024)
    create_if_missing: bool = Field(default=False)
    bootstrap_materials: bool = Field(default=False)


class HostReadFileRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


def _unwrap_bridge_response(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("ok"):
        return result.get("data", {})

    data = result.get("data", {}) or {}
    detail = data.get("error") or data.get("detail") or "Desktop bridge request failed"
    raise HTTPException(status_code=result.get("status_code", 503), detail=detail)


@router.get("/bridge/health", response_model=ApiResponse)
async def get_bridge_health(_: User = Depends(require_user)):
    result = await request_desktop_bridge("GET", "/health", timeout=5.0)
    if result.get("ok"):
        data = result.get("data", {})
        payload = {
            "available": True,
            "bridge_url": result.get("base_url", ""),
            **(data if isinstance(data, dict) else {}),
        }
        return ApiResponse(data=payload)
    return ApiResponse(
        data={
            "available": False,
            "bridge_url": "",
            "error": (result.get("data", {}) or {}).get("error", "Desktop bridge unavailable"),
        }
    )


@router.post("/obsidian/pick-directory", response_model=ApiResponse)
async def pick_obsidian_directory(
    body: PickDirectoryRequest,
    _: User = Depends(require_user),
):
    result = await request_desktop_bridge("POST", "/pick-directory", body.model_dump(), timeout=60.0)
    data = _unwrap_bridge_response(result)
    if isinstance(data, dict):
        data["bridge_url"] = result.get("base_url", "")
    return ApiResponse(data=data)


@router.post("/obsidian/test-vault", response_model=ApiResponse)
async def test_obsidian_vault(
    body: EnsureVaultRequest,
    _: User = Depends(require_user),
):
    payload = {
        "vault_dir": body.vault_dir,
        "create_if_missing": body.create_if_missing,
        "bootstrap_materials": body.bootstrap_materials,
    }
    result = await request_desktop_bridge("POST", "/obsidian/ensure-vault", payload, timeout=20.0)
    data = _unwrap_bridge_response(result)
    if isinstance(data, dict):
        data["bridge_url"] = result.get("base_url", "")
    return ApiResponse(data=data)


@router.post("/host/read-file", response_model=ApiResponse)
async def host_read_file(
    body: HostReadFileRequest,
    _: User = Depends(require_user),
):
    result = await request_desktop_bridge("POST", "/host/read-file", body.model_dump(), timeout=60.0)
    data = _unwrap_bridge_response(result)
    if isinstance(data, dict):
        data["bridge_url"] = result.get("base_url", "")
    return ApiResponse(data=data)
