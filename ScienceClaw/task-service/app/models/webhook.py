"""Webhook models for notification channels."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

WEBHOOK_TYPES = {"feishu", "dingtalk", "wecom", "telegram"}
LEGACY_URL_WEBHOOK_TYPES = {"feishu", "dingtalk", "wecom"}


class TelegramWebhookConfig(BaseModel):
    bot_token: str = Field(default="", description="Telegram bot token")
    chat_id: str = Field(default="", description="Telegram chat id")


class WebhookCreate(BaseModel):
    name: str = Field(..., description="Webhook display name")
    type: str = Field(..., description="feishu | dingtalk | wecom | telegram")
    url: str = Field(default="", description="Legacy webhook URL")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Structured webhook config")


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class WebhookOut(BaseModel):
    id: str
    name: str
    type: str
    url: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def normalize_webhook_storage(
    webhook_type: str,
    *,
    url: str = "",
    config: Optional[Dict[str, Any]] = None,
    existing_config: Optional[Dict[str, Any]] = None,
) -> tuple[str, Dict[str, Any]]:
    normalized_type = str(webhook_type or "").strip().lower()
    raw_url = str(url or "").strip()
    raw_config = dict(config or {})
    if normalized_type in LEGACY_URL_WEBHOOK_TYPES:
        return raw_url, {}
    if normalized_type != "telegram":
        return raw_url, raw_config

    merged_config = dict(existing_config or {})
    incoming_token = str(raw_config.get("bot_token") or "").strip()
    incoming_chat_id = str(raw_config.get("chat_id") or "").strip()
    if incoming_token:
        merged_config["bot_token"] = incoming_token
    if incoming_chat_id:
        merged_config["chat_id"] = incoming_chat_id
    return "", merged_config


def validate_webhook_payload(
    webhook_type: str,
    *,
    name: str,
    url: str = "",
    config: Optional[Dict[str, Any]] = None,
) -> None:
    normalized_type = str(webhook_type or "").strip().lower()
    if normalized_type not in WEBHOOK_TYPES:
        raise ValueError(f"Invalid type. Must be one of: {', '.join(sorted(WEBHOOK_TYPES))}")
    if not str(name or "").strip():
        raise ValueError("Name is required")
    if normalized_type in LEGACY_URL_WEBHOOK_TYPES and not str(url or "").strip():
        raise ValueError("URL is required")
    if normalized_type == "telegram":
        bot_token = str((config or {}).get("bot_token") or "").strip()
        chat_id = str((config or {}).get("chat_id") or "").strip()
        if not bot_token:
            raise ValueError("Telegram bot token is required")
        if not chat_id:
            raise ValueError("Telegram chat id is required")


def _public_config(webhook_type: str, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_type = str(webhook_type or "").strip().lower()
    raw_config = dict(config or {})
    if normalized_type != "telegram":
        return raw_config
    bot_token = str(raw_config.get("bot_token") or "")
    chat_id = str(raw_config.get("chat_id") or "")
    return {
        "chat_id": chat_id,
        "has_bot_token": bool(bot_token),
        "bot_token_masked": "********" if bot_token else "",
    }


def webhook_doc_to_out(doc: Dict[str, Any]) -> WebhookOut:
    wid = doc.get("_id")
    if hasattr(wid, "hex"):
        wid = str(wid)
    webhook_type = doc.get("type", "feishu")
    return WebhookOut(
        id=str(wid),
        name=doc.get("name", ""),
        type=webhook_type,
        url=doc.get("url", ""),
        config=_public_config(webhook_type, doc.get("config")),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
