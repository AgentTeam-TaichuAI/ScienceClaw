from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.config import settings
from backend.mongodb.db import db


IM_SETTINGS_COLLECTION = "im_system_settings"
IM_SETTINGS_DOC_ID = "global"


class IMSystemSettings(BaseModel):
    im_enabled: bool = False
    im_response_timeout: int = Field(default=300, ge=30, le=1800)
    im_max_message_length: int = Field(default=4000, ge=500, le=20000)
    lark_enabled: bool = False
    lark_app_id: str = ""
    lark_app_secret: str = ""
    wechat_enabled: bool = False
    im_progress_mode: str = Field(default="card_entity")
    im_progress_detail_level: str = Field(default="detailed")
    im_progress_interval_ms: int = Field(default=1200, ge=300, le=10000)
    im_realtime_events: list[str] = Field(default_factory=lambda: ["plan_update"])


class UpdateIMSystemSettingsRequest(BaseModel):
    im_enabled: Optional[bool] = None
    im_response_timeout: Optional[int] = Field(default=None, ge=30, le=1800)
    im_max_message_length: Optional[int] = Field(default=None, ge=500, le=20000)
    lark_enabled: Optional[bool] = None
    lark_app_id: Optional[str] = None
    lark_app_secret: Optional[str] = None
    wechat_enabled: Optional[bool] = None
    im_progress_mode: Optional[str] = None
    im_progress_detail_level: Optional[str] = None
    im_progress_interval_ms: Optional[int] = Field(default=None, ge=300, le=10000)
    im_realtime_events: Optional[list[str]] = None


def get_env_default_im_settings() -> IMSystemSettings:
    return IMSystemSettings(
        im_enabled=settings.im_enabled,
        im_response_timeout=settings.im_response_timeout,
        im_max_message_length=settings.im_max_message_length,
        lark_enabled=settings.lark_enabled,
        lark_app_id=settings.lark_app_id,
        lark_app_secret=settings.lark_app_secret,
    )


async def get_im_system_settings() -> IMSystemSettings:
    collection = db.get_collection(IM_SETTINGS_COLLECTION)
    doc = await collection.find_one({"_id": IM_SETTINGS_DOC_ID})
    if doc:
        doc.pop("_id", None)
        return IMSystemSettings(**doc)
    defaults = get_env_default_im_settings()
    payload = defaults.model_dump()
    payload["_id"] = IM_SETTINGS_DOC_ID
    await collection.update_one({"_id": IM_SETTINGS_DOC_ID}, {"$set": payload}, upsert=True)
    return defaults


async def update_im_system_settings(updates: UpdateIMSystemSettingsRequest) -> IMSystemSettings:
    current = await get_im_system_settings()
    merged = current.model_dump()
    update_data = updates.model_dump(exclude_unset=True)
    if "lark_app_secret" in update_data and (update_data["lark_app_secret"] or "").strip() == "":
        update_data.pop("lark_app_secret")
    if "im_progress_mode" in update_data:
        progress_mode = str(update_data["im_progress_mode"] or "").strip()
        if progress_mode not in ("text_multi", "card_entity"):
            update_data["im_progress_mode"] = "text_multi"
    if "im_progress_detail_level" in update_data:
        detail_level = str(update_data["im_progress_detail_level"] or "").strip()
        if detail_level not in ("compact", "detailed"):
            update_data["im_progress_detail_level"] = "detailed"
    if "im_realtime_events" in update_data:
        allowed_events = {"plan_update", "planning_message", "tool_call", "tool_result", "error"}
        raw_events = update_data.get("im_realtime_events") or []
        normalized_events: list[str] = []
        seen_events: set[str] = set()
        for event in raw_events:
            event_name = str(event or "").strip()
            if event_name in allowed_events and event_name not in seen_events:
                normalized_events.append(event_name)
                seen_events.add(event_name)
        update_data["im_realtime_events"] = normalized_events
    merged.update(update_data)
    updated = IMSystemSettings(**merged)
    payload = updated.model_dump()
    payload["_id"] = IM_SETTINGS_DOC_ID
    await db.get_collection(IM_SETTINGS_COLLECTION).update_one(
        {"_id": IM_SETTINGS_DOC_ID},
        {"$set": payload},
        upsert=True,
    )
    return updated


def to_public_settings_dict(im_settings: IMSystemSettings) -> dict:
    return {
        "im_enabled": im_settings.im_enabled,
        "im_response_timeout": im_settings.im_response_timeout,
        "im_max_message_length": im_settings.im_max_message_length,
        "lark_enabled": im_settings.lark_enabled,
        "lark_app_id": im_settings.lark_app_id,
        "has_lark_app_secret": bool(im_settings.lark_app_secret),
        "lark_app_secret_masked": "********" if im_settings.lark_app_secret else "",
        "wechat_enabled": im_settings.wechat_enabled,
        "im_progress_mode": im_settings.im_progress_mode,
        "im_progress_detail_level": im_settings.im_progress_detail_level,
        "im_progress_interval_ms": im_settings.im_progress_interval_ms,
        "im_realtime_events": im_settings.im_realtime_events,
    }
