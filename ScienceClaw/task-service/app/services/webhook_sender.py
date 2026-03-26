"""Multi-platform webhook sender."""
from __future__ import annotations

from typing import Any, Dict, Tuple

import httpx
from loguru import logger


def _feishu_card(title: str, content: str, *, color: str = "blue") -> dict:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title[:100]},
                "template": color,
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content[:4000]}},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "ScienceClaw 定时任务"}]},
            ],
        },
    }


async def _send_feishu(url: str, title: str, content: str, config: Dict[str, Any]) -> bool:
    is_success = "成功" in title
    is_fail = "失败" in title
    color = "green" if is_success else ("red" if is_fail else "blue")
    body = _feishu_card(title, content, color=color)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"Feishu webhook failed: {r.status_code} {r.text[:200]}")
            return False
        data = r.json()
        return data.get("code") in (None, 0)


def _dingtalk_actioncard(title: str, content: str) -> dict:
    is_success = "成功" in title
    is_fail = "失败" in title
    icon = "✅" if is_success else ("❌" if is_fail else "🔔")
    color = "#07C160" if is_success else ("#FF4D4F" if is_fail else "#1890FF")
    md = (
        f"## <font color=\"{color}\">{icon} {title}</font>\n\n"
        f"---\n\n"
        f"{content[:4000]}\n\n"
        f"---\n\n"
        f"> ScienceClaw 定时任务"
    )
    return {
        "msgtype": "actionCard",
        "actionCard": {
            "title": title[:100],
            "text": md,
            "hideAvatar": "0",
            "btnOrientation": "0",
        },
    }


async def _send_dingtalk(url: str, title: str, content: str, config: Dict[str, Any]) -> bool:
    body = _dingtalk_actioncard(title, content)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"DingTalk webhook failed: {r.status_code} {r.text[:200]}")
            return False
        data = r.json()
        return data.get("errcode") == 0


def _wecom_markdown(title: str, content: str) -> dict:
    is_success = "成功" in title
    is_fail = "失败" in title
    icon = "✅" if is_success else ("❌" if is_fail else "🔔")
    color = "info" if is_success else ("warning" if is_fail else "comment")
    md = (
        f"### {icon} {title}\n\n"
        f"{content[:4000]}\n\n"
        f"> <font color=\"{color}\">ScienceClaw 定时任务</font>"
    )
    return {
        "msgtype": "markdown",
        "markdown": {"content": md},
    }


async def _send_wecom(url: str, title: str, content: str, config: Dict[str, Any]) -> bool:
    body = _wecom_markdown(title, content)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"WeCom webhook failed: {r.status_code} {r.text[:200]}")
            return False
        data = r.json()
        return data.get("errcode") == 0


async def _send_telegram(url: str, title: str, content: str, config: Dict[str, Any]) -> bool:
    bot_token = str(config.get("bot_token") or "").strip()
    chat_id = str(config.get("chat_id") or "").strip()
    if not bot_token or not chat_id:
        raise ValueError("Telegram bot token or chat id is missing")
    message_text = f"{title}\n\n{content}".strip()
    if len(message_text) > 4096:
        message_text = message_text[:4093] + "..."
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            api_url,
            json={
                "chat_id": int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id,
                "text": message_text,
                "disable_web_page_preview": True,
            },
        )
        if r.status_code != 200:
            logger.warning(f"Telegram webhook failed: {r.status_code} {r.text[:200]}")
            return False
        data = r.json()
        return bool(data.get("ok"))


_SENDERS = {
    "feishu": _send_feishu,
    "dingtalk": _send_dingtalk,
    "wecom": _send_wecom,
    "telegram": _send_telegram,
}


async def send_webhook(
    webhook_type: str,
    url: str,
    title: str,
    content: str,
    config: Dict[str, Any] | None = None,
) -> bool:
    sender = _SENDERS.get(webhook_type, _send_feishu)
    try:
        return await sender(url, title, content, dict(config or {}))
    except Exception as e:
        logger.warning(f"Webhook send failed ({webhook_type}): {e}")
        return False


async def send_test_message(
    webhook_type: str,
    webhook_url: str,
    webhook_name: str,
    webhook_config: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    config = dict(webhook_config or {})
    if webhook_type == "telegram":
        if not str(config.get("bot_token") or "").strip():
            return False, "Telegram bot token is empty"
        if not str(config.get("chat_id") or "").strip():
            return False, "Telegram chat id is empty"
    elif not webhook_url or not webhook_url.strip():
        return False, "Webhook URL is empty"

    name = webhook_name or "Webhook"
    title = f"Webhook 验证 - {name}"
    content = (
        "**验证信息**\n"
        "这是一条来自 ScienceClaw 的测试消息。\n\n"
        "如果您收到了这条消息，说明通知渠道配置正确。"
    )
    try:
        ok = await send_webhook(webhook_type, webhook_url.strip(), title, content, config)
        if ok:
            return True, "验证成功，请检查对应频道中的测试消息"
        return False, "发送失败，请检查渠道配置是否有效"
    except Exception as e:
        return False, str(e)
