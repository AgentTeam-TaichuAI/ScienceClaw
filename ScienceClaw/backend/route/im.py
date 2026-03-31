from __future__ import annotations

import ipaddress
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from backend.im.base import IMPlatform
from backend.im.lark_long_connection import LarkLongConnectionService
from backend.im.orchestrator import IMServiceOrchestrator
from backend.im.session_manager import IMSessionManager
from backend.im.system_settings import (
    IMSystemSettings,
    UpdateIMSystemSettingsRequest,
    get_im_system_settings,
    to_public_settings_dict,
    update_im_system_settings,
)
from backend.im.telegram_polling import TelegramPollingService
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


class TelegramBindRequest(BaseModel):
    telegram_user_id: str


class TelegramBindLinkData(BaseModel):
    configured: bool = False
    username: Optional[str] = None
    bot_link: Optional[str] = None
    deep_link: Optional[str] = None
    start_parameter: Optional[str] = None
    expires_at: Optional[int] = None


class FeishuSetupRequest(BaseModel):
    app_id: str
    app_secret: str


_orchestrator: Optional[IMServiceOrchestrator] = None
_lark_long_connection_service: Optional[LarkLongConnectionService] = None
_telegram_polling_service: Optional[TelegramPollingService] = None
_binding_manager = IMUserBindingManager()
_binding_service = IMUserBindingService(_binding_manager)
_session_manager = IMSessionManager()


def _build_orchestrator(im_settings: IMSystemSettings) -> IMServiceOrchestrator:
    return IMServiceOrchestrator(
        progress_mode=im_settings.im_progress_mode,
        progress_detail_level=im_settings.im_progress_detail_level,
        progress_interval_ms=im_settings.im_progress_interval_ms,
        realtime_events=im_settings.im_realtime_events,
        max_message_length=im_settings.im_max_message_length,
        telegram_send_output_files=im_settings.telegram_send_output_files,
    )


async def _register_enabled_adapters(orchestrator: IMServiceOrchestrator, im_settings: IMSystemSettings) -> None:
    if im_settings.lark_enabled and im_settings.lark_app_id and im_settings.lark_app_secret:
        from backend.im.adapters.lark import LarkAdapter, LarkMessageFormatter

        lark_adapter = LarkAdapter(
            app_id=im_settings.lark_app_id,
            app_secret=im_settings.lark_app_secret,
            max_message_length=im_settings.im_max_message_length,
        )
        orchestrator.register_adapter(IMPlatform.LARK, lark_adapter, LarkMessageFormatter())

    if im_settings.telegram_enabled and im_settings.telegram_bot_token:
        from backend.im.adapters.telegram import TelegramAdapter, TelegramMessageFormatter

        telegram_adapter = TelegramAdapter(
            bot_token=im_settings.telegram_bot_token,
            webhook_secret=im_settings.telegram_webhook_secret,
            public_base_url=im_settings.telegram_public_base_url,
            max_message_length=im_settings.im_max_message_length,
        )
        try:
            await telegram_adapter.get_me()
        except Exception as exc:
            logger.warning(f"telegram getMe failed during runtime init: {exc}")
        try:
            await telegram_adapter.sync_bot_commands()
        except Exception as exc:
            logger.warning(f"telegram sync bot commands failed during runtime init: {exc}")
        orchestrator.register_adapter(IMPlatform.TELEGRAM, telegram_adapter, TelegramMessageFormatter())


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


def _build_telegram_polling_service(
    orchestrator: IMServiceOrchestrator,
    im_settings: IMSystemSettings,
) -> Optional[TelegramPollingService]:
    if not im_settings.im_enabled:
        return None
    if im_settings.telegram_ingress_mode != "polling":
        return None
    adapter = orchestrator.adapters.get(IMPlatform.TELEGRAM)
    if adapter is None:
        return None
    return TelegramPollingService(orchestrator=orchestrator, adapter=adapter)


async def _setup_telegram_ingress(orchestrator: IMServiceOrchestrator, im_settings: IMSystemSettings) -> Optional[TelegramPollingService]:
    adapter = orchestrator.adapters.get(IMPlatform.TELEGRAM)
    if adapter is None or not im_settings.im_enabled:
        return None
    if im_settings.telegram_ingress_mode == "webhook":
        await adapter.set_webhook()
        return None
    await adapter.delete_webhook(drop_pending_updates=False)
    service = _build_telegram_polling_service(orchestrator, im_settings)
    if service:
        await service.start()
    return service


async def _stop_runtime_services() -> None:
    global _lark_long_connection_service, _telegram_polling_service
    if _lark_long_connection_service:
        await _lark_long_connection_service.stop()
        _lark_long_connection_service = None
    if _telegram_polling_service:
        await _telegram_polling_service.stop()
        _telegram_polling_service = None


async def reload_im_runtime() -> Optional[IMServiceOrchestrator]:
    global _orchestrator, _lark_long_connection_service, _telegram_polling_service
    im_settings = await get_im_system_settings()
    await _stop_runtime_services()
    orchestrator = _build_orchestrator(im_settings)
    await _register_enabled_adapters(orchestrator, im_settings)
    _orchestrator = orchestrator
    _lark_long_connection_service = _build_lark_long_connection_service(orchestrator, im_settings)
    if _lark_long_connection_service:
        await _lark_long_connection_service.start()
    _telegram_polling_service = await _setup_telegram_ingress(orchestrator, im_settings)
    return orchestrator


async def start_im_runtime() -> Optional[IMServiceOrchestrator]:
    orchestrator = await reload_im_runtime()
    im_settings = await get_im_system_settings()
    if im_settings.wechat_enabled:
        bridge = WeChatBridge.get_instance()
        if not bridge.is_running:
            await bridge.start_with_saved_token()
    return orchestrator


async def stop_im_runtime() -> None:
    await _stop_runtime_services()

    bridge = WeChatBridge.get_instance()
    if bridge.is_running:
        await bridge.stop()


def require_admin_user(current_user: User = Depends(require_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


def _serialize_binding(binding: Any) -> dict:
    return {
        "bound": True,
        "platform": binding.platform.value,
        "platform_user_id": binding.platform_user_id,
        "science_user_id": binding.science_user_id,
        "status": binding.status,
        "updated_at": binding.updated_at,
    }


async def _get_telegram_adapter() -> Any:
    orchestrator = _orchestrator
    if orchestrator is None:
        return None
    return orchestrator.adapters.get(IMPlatform.TELEGRAM)


async def _resolve_telegram_bot_identity(adapter: Any) -> tuple[Optional[int], str]:
    if adapter is None:
        return None, ""
    username = str(getattr(adapter, "_bot_username", "") or "")
    bot_id = getattr(adapter, "_bot_id", None)
    if username:
        return bot_id, username
    info = await adapter.get_me()
    return info.get("id"), str(info.get("username") or "")


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
    return ApiResponse(data=_serialize_binding(binding))


@router.delete("/bind/lark", response_model=ApiResponse)
async def unbind_lark_user(current_user: User = Depends(require_user)):
    removed = await _binding_service.unbind_lark_user(science_user_id=current_user.id)
    await _session_manager.release_owned_conversations(platform=IMPlatform.LARK, science_user_id=current_user.id)
    return ApiResponse(data={"removed": removed})


@router.get("/bind/lark/status", response_model=ApiResponse)
async def get_lark_bind_status(current_user: User = Depends(require_user)):
    binding = await _binding_service.get_lark_binding_status(science_user_id=current_user.id)
    if not binding:
        return ApiResponse(data={"bound": False})
    return ApiResponse(data=_serialize_binding(binding))


@router.post("/bind/telegram", response_model=ApiResponse)
async def bind_telegram_user(body: TelegramBindRequest, current_user: User = Depends(require_user)):
    try:
        binding = await _binding_service.bind_telegram_user(
            science_user_id=current_user.id,
            raw_telegram_user_id=body.telegram_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=_serialize_binding(binding))


@router.delete("/bind/telegram", response_model=ApiResponse)
async def unbind_telegram_user(current_user: User = Depends(require_user)):
    removed = await _binding_service.unbind_telegram_user(science_user_id=current_user.id)
    await _session_manager.release_owned_conversations(platform=IMPlatform.TELEGRAM, science_user_id=current_user.id)
    return ApiResponse(data={"removed": removed})


@router.get("/bind/telegram/status", response_model=ApiResponse)
async def get_telegram_bind_status(current_user: User = Depends(require_user)):
    binding = await _binding_service.get_telegram_binding_status(science_user_id=current_user.id)
    if not binding:
        return ApiResponse(data={"bound": False})
    return ApiResponse(data=_serialize_binding(binding))


@router.post("/bind/telegram/link", response_model=ApiResponse)
async def create_telegram_bind_link(current_user: User = Depends(require_user)):
    existing = await _binding_service.get_telegram_binding_status(science_user_id=current_user.id)
    if existing:
        return ApiResponse(
            data=TelegramBindLinkData(
                configured=True,
                bot_link=None,
                deep_link=None,
                start_parameter=None,
                expires_at=None,
            ).model_dump()
        )

    adapter = await _get_telegram_adapter()
    if adapter is None:
        raise HTTPException(status_code=400, detail="Telegram bot is not configured")

    try:
        _, username = await _resolve_telegram_bot_identity(adapter)
    except Exception as exc:
        logger.warning(f"fetch telegram bot identity failed: {exc}")
        raise HTTPException(status_code=400, detail="Telegram bot is not ready yet") from exc

    if not username:
        raise HTTPException(status_code=400, detail="Telegram bot username is unavailable")

    binding_token = await _binding_service.create_telegram_binding_token(science_user_id=current_user.id)
    start_parameter = f"bind_{binding_token.token}"
    bot_link = f"https://t.me/{username}"
    return ApiResponse(
        data=TelegramBindLinkData(
            configured=True,
            username=username,
            bot_link=bot_link,
            deep_link=f"{bot_link}?start={start_parameter}",
            start_parameter=start_parameter,
            expires_at=binding_token.expires_at,
        ).model_dump()
    )


@router.get("/telegram/bot-info", response_model=ApiResponse)
async def get_telegram_bot_info(_: User = Depends(require_user)):
    adapter = await _get_telegram_adapter()
    if adapter is None:
        return ApiResponse(data={"configured": False})
    username = str(getattr(adapter, "_bot_username", "") or "")
    if not username:
        try:
            bot_id, username = await _resolve_telegram_bot_identity(adapter)
        except Exception as exc:
            logger.warning(f"fetch telegram bot info failed: {exc}")
            bot_id, username = None, ""
    else:
        bot_id = getattr(adapter, "_bot_id", None)
    return ApiResponse(
        data={
            "configured": True,
            "bot_id": bot_id,
            "username": username,
            "bot_link": f"https://t.me/{username}" if username else "",
        }
    )


@router.post("/webhook/telegram", response_model=ApiResponse)
async def telegram_webhook(request: Request):
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="IM runtime not initialized")
    result = await _orchestrator.handle_webhook(IMPlatform.TELEGRAM, request)
    return ApiResponse(data=result)


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


@router.post("/internal/feishu-setup", response_model=ApiResponse)
async def internal_feishu_setup(body: FeishuSetupRequest, request: Request):
    client_ip = request.client.host if request.client else ""
    if not _is_internal_ip(client_ip):
        logger.warning(f"[IM] feishu-setup rejected from non-internal IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Internal network only")

    logger.info(f"[IM] feishu-setup from {client_ip}: app_id={body.app_id[:8]}...")
    await update_im_system_settings(
        UpdateIMSystemSettingsRequest(
            lark_enabled=True,
            lark_app_id=body.app_id,
            lark_app_secret=body.app_secret,
        )
    )
    await reload_im_runtime()
    return ApiResponse(data={"saved": True, "app_id": body.app_id})
