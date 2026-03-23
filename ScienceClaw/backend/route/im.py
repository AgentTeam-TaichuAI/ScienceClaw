from __future__ import annotations

import ipaddress
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from backend.im.base import IMPlatform
from backend.im.lark_long_connection import LarkLongConnectionService
from backend.im.orchestrator import IMServiceOrchestrator
from backend.im.system_settings import (
    IMSystemSettings,
    UpdateIMSystemSettingsRequest,
    get_im_system_settings,
    to_public_settings_dict,
    update_im_system_settings,
)
from backend.im.user_binding import IMUserBindingManager
from backend.im.user_binding_service import IMUserBindingService
from backend.im.wechat_bridge import WeChatBridge
from backend.user.dependencies import User, require_user

router = APIRouter(prefix="/im", tags=["im"])


class ApiResponse(BaseModel):
    code: int = Field(default=0)
    msg: str = Field(default="ok")
    data: Any = Field(default=None)


class LarkBindRequest(BaseModel):
    lark_user_id: str
    lark_union_id: Optional[str] = None


_orchestrator: Optional[IMServiceOrchestrator] = None
_lark_long_connection_service: Optional[LarkLongConnectionService] = None
_binding_manager = IMUserBindingManager()
_binding_service = IMUserBindingService(_binding_manager)


def _build_orchestrator(im_settings: IMSystemSettings) -> IMServiceOrchestrator:
    orchestrator = IMServiceOrchestrator(
        progress_mode=im_settings.im_progress_mode,
        progress_detail_level=im_settings.im_progress_detail_level,
        progress_interval_ms=im_settings.im_progress_interval_ms,
        realtime_events=im_settings.im_realtime_events,
        max_message_length=im_settings.im_max_message_length,
    )
    if im_settings.lark_enabled and im_settings.lark_app_id and im_settings.lark_app_secret:
        from backend.im.adapters.lark import LarkAdapter, LarkMessageFormatter

        lark_adapter = LarkAdapter(
            app_id=im_settings.lark_app_id,
            app_secret=im_settings.lark_app_secret,
            max_message_length=im_settings.im_max_message_length,
        )
        lark_formatter = LarkMessageFormatter()
        orchestrator.register_adapter(IMPlatform.LARK, lark_adapter, lark_formatter)
    return orchestrator


def _build_lark_long_connection_service(
    orchestrator: IMServiceOrchestrator,
    im_settings: IMSystemSettings,
) -> Optional[LarkLongConnectionService]:
    if not im_settings.im_enabled:
        return None
    adapter = orchestrator.adapters.get(IMPlatform.LARK)
    if adapter is None:
        return None
    return LarkLongConnectionService(orchestrator=orchestrator, adapter=adapter)


async def reload_im_runtime() -> Optional[LarkLongConnectionService]:
    global _orchestrator, _lark_long_connection_service
    im_settings = await get_im_system_settings()
    old_service = _lark_long_connection_service
    _lark_long_connection_service = None
    if old_service:
        await old_service.stop()
    orchestrator = _build_orchestrator(im_settings)
    _orchestrator = orchestrator
    service = _build_lark_long_connection_service(orchestrator, im_settings)
    if service:
        await service.start()
    _lark_long_connection_service = service
    return service


async def start_im_runtime() -> Optional[LarkLongConnectionService]:
    service = await reload_im_runtime()

    im_settings = await get_im_system_settings()
    if im_settings.wechat_enabled:
        bridge = WeChatBridge.get_instance()
        if not bridge.is_running:
            await bridge.start_with_saved_token()

    return service


async def stop_im_runtime():
    global _lark_long_connection_service
    if _lark_long_connection_service:
        await _lark_long_connection_service.stop()
        _lark_long_connection_service = None

    bridge = WeChatBridge.get_instance()
    if bridge.is_running:
        await bridge.stop()


def require_admin_user(current_user: User = Depends(require_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


@router.post("/bind/lark", response_model=ApiResponse)
async def bind_lark_user(body: LarkBindRequest, current_user: User = Depends(require_user)):
    try:
        binding = await _binding_service.bind_lark_user(
            science_user_id=current_user.id,
            raw_lark_user_id=body.lark_user_id,
            lark_union_id=body.lark_union_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(
        data={
            "platform": binding.platform.value,
            "platform_user_id": binding.platform_user_id,
            "science_user_id": binding.science_user_id,
            "status": binding.status,
        }
    )


@router.delete("/bind/lark", response_model=ApiResponse)
async def unbind_lark_user(current_user: User = Depends(require_user)):
    removed = await _binding_service.unbind_lark_user(science_user_id=current_user.id)
    return ApiResponse(data={"removed": removed})


@router.get("/bind/lark/status", response_model=ApiResponse)
async def get_lark_bind_status(current_user: User = Depends(require_user)):
    binding = await _binding_service.get_lark_binding_status(science_user_id=current_user.id)
    if not binding:
        return ApiResponse(data={"bound": False})
    return ApiResponse(
        data={
            "bound": True,
            "platform": binding.platform.value,
            "platform_user_id": binding.platform_user_id,
            "science_user_id": binding.science_user_id,
            "status": binding.status,
            "updated_at": binding.updated_at,
        }
    )


@router.get("/settings", response_model=ApiResponse)
async def get_im_settings(_: User = Depends(require_admin_user)):
    im_settings = await get_im_system_settings()
    return ApiResponse(data=to_public_settings_dict(im_settings))


@router.put("/settings", response_model=ApiResponse)
async def update_im_settings(
    body: UpdateIMSystemSettingsRequest,
    _: User = Depends(require_admin_user),
):
    updated = await update_im_system_settings(body)
    await reload_im_runtime()
    return ApiResponse(data=to_public_settings_dict(updated))


# ── WeChat Bridge endpoints ──────────────────────────────────────────────────


@router.post("/wechat/start", response_model=ApiResponse)
async def start_wechat_bridge(
    current_user: User = Depends(require_admin_user),
):
    """Start WeChat QR login flow."""
    bridge = WeChatBridge.get_instance()
    result = await bridge.start_login(admin_user_id=current_user.id)
    return ApiResponse(data=result)


@router.post("/wechat/resume", response_model=ApiResponse)
async def resume_wechat_bridge(
    current_user: User = Depends(require_admin_user),
):
    """Resume WeChat connection with saved token."""
    bridge = WeChatBridge.get_instance()
    result = await bridge.start_with_saved_token(admin_user_id=current_user.id)
    return ApiResponse(data=result)


@router.post("/wechat/stop", response_model=ApiResponse)
async def stop_wechat_bridge(_: User = Depends(require_admin_user)):
    """Stop WeChat bridge (keeps saved token for later resume)."""
    bridge = WeChatBridge.get_instance()
    result = await bridge.stop()
    return ApiResponse(data=result)


@router.post("/wechat/logout", response_model=ApiResponse)
async def logout_wechat_bridge(_: User = Depends(require_admin_user)):
    """Stop and clear all saved WeChat credentials."""
    bridge = WeChatBridge.get_instance()
    result = await bridge.logout()
    return ApiResponse(data=result)


@router.get("/wechat/status", response_model=ApiResponse)
async def get_wechat_bridge_status(
    output_offset: int = 0,
    _: User = Depends(require_admin_user),
):
    """Get WeChat bridge status, QR code, and logs."""
    bridge = WeChatBridge.get_instance()
    return ApiResponse(data=bridge.get_status(output_offset))


# ── Internal endpoint (sandbox → backend, no user auth) ─────────────────────


_INTERNAL_NETWORKS = [
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]


def _is_internal_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _INTERNAL_NETWORKS)
    except ValueError:
        return False


class FeishuSetupRequest(BaseModel):
    app_id: str
    app_secret: str


@router.post("/internal/feishu-setup", response_model=ApiResponse)
async def internal_feishu_setup(body: FeishuSetupRequest, request: Request):
    """Save Feishu credentials from sandbox automation (internal network only)."""
    client_ip = request.client.host if request.client else ""
    if not _is_internal_ip(client_ip):
        logger.warning(f"[IM] feishu-setup rejected from non-internal IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Internal network only")

    logger.info(f"[IM] feishu-setup from {client_ip}: app_id={body.app_id[:8]}...")
    await update_im_system_settings(UpdateIMSystemSettingsRequest(
        lark_enabled=True,
        lark_app_id=body.app_id,
        lark_app_secret=body.app_secret,
    ))
    await reload_im_runtime()
    return ApiResponse(data={"saved": True, "app_id": body.app_id})
