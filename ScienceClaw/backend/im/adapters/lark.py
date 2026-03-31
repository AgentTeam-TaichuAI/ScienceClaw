from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple

try:
    import lark_oapi as lark
except Exception:
    lark = None
from fastapi import Request
from loguru import logger

from backend.im.base import IMAdapter, IMChat, IMMessage, IMMessageFormatter, IMPlatform, IMResponse, IMUser

class LarkAdapter(IMAdapter):
    platform = IMPlatform.LARK
    supports_card_entity = True

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        max_message_length: int = 4000,
    ):
        if lark is None:
            raise RuntimeError("lark-oapi is required for LarkAdapter")
        self.app_id = app_id
        self.app_secret = app_secret
        self._client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()
        self._card_entity_available = True
        self._card_permission_warned = False
        self._max_message_length = max(500, min(int(max_message_length), 20000))

    def get_webhook_path(self) -> str:
        return ""

    async def verify_webhook(self, request: Request) -> bool:
        return True

    async def parse_message(self, request: Request) -> Optional[IMMessage]:
        try:
            data = await request.json()
            return self.parse_event_data(data)
        except Exception as exc:
            logger.exception(f"parse lark message failed: {exc}")
            return None

    async def send_message(self, chat: IMChat, response: IMResponse) -> bool:
        ok, _ = await self.send_message_with_id(chat, response)
        return ok

    async def send_message_with_id(self, chat: IMChat, response: IMResponse) -> Tuple[bool, Optional[str]]:
        content = self._convert_response_to_lark_format(response)
        if content["msg_type"] == "card_entity":
            return await self._send_card_entity(chat, content["content"], response)
        return await self._send_raw_message(chat, content["msg_type"], content["content"], response)

    async def update_message(self, message_id: str, response: IMResponse) -> bool:
        content = self._convert_response_to_lark_format(response)
        if content["msg_type"] == "card_entity":
            card_content = self._sanitize_card_content(content["content"])
            # PATCH /im/v1/messages/{id}: content is the card JSON directly, no {"card": ...} wrapper
            return await self._patch_raw_message(message_id, "interactive", card_content)
        return await self._patch_raw_message(message_id, content["msg_type"], content["content"])

    async def send_typing_indicator(self, chat: IMChat) -> None:
        return None

    async def handle_url_verification(self, request: Request) -> Optional[Dict[str, Any]]:
        return None

    def parse_event_data(self, data: Dict[str, Any]) -> Optional[IMMessage]:
        header = data.get("header", {})
        event_type = header.get("event_type")
        if event_type != "im.message.receive_v1":
            return None
        event = data.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        msg_type = message.get("message_type", message.get("msg_type", "text"))
        content_str = message.get("content", "{}")
        try:
            content = json.loads(content_str)
        except json.JSONDecodeError:
            content = {"text": content_str}
        text_content = ""
        if msg_type == "text":
            text_content = content.get("text", "")
        elif msg_type == "post":
            text_content = self._extract_text_from_post(content)
        mentions = event.get("mentions", [])
        is_at_me = any(str(m.get("name") or "").strip() for m in mentions)
        sender_id = sender.get("sender_id", {})
        open_id = sender_id.get("open_id", "")
        union_id = sender_id.get("union_id", "")
        chat_type = message.get("chat_type", "p2p")
        parsed_message = IMMessage(
            platform=self.platform,
            message_id=message.get("message_id", ""),
            delivery_id=message.get("message_id", ""),
            user=IMUser(
                platform=self.platform,
                platform_user_id=open_id,
                platform_union_id=union_id,
            ),
            chat=IMChat(
                platform=self.platform,
                chat_id=message.get("chat_id", ""),
                chat_type="group" if chat_type == "group" else "p2p",
                thread_id=message.get("thread_id") or message.get("thread_key"),
                root_id=message.get("root_id"),
            ),
            content_type="text" if msg_type in ("text", "post") else msg_type,
            content=text_content,
            raw_message=data,
            timestamp=int(message.get("create_time", "0")) // 1000,
            is_at_me=is_at_me,
        )
        logger.info(
            "[Lark] received message: "
            f"message_id={parsed_message.message_id}, "
            f"chat_type={parsed_message.chat.chat_type}, "
            f"user_open_id={parsed_message.user.platform_user_id or '-'}, "
            f"is_at_me={parsed_message.is_at_me}, "
            f"content_type={parsed_message.content_type}, "
            f"content_preview={parsed_message.content[:80]!r}"
        )
        return parsed_message

    def build_long_connection_handler(
        self,
        on_message: Callable[[IMMessage], None],
    ):
        def _handle_p2(data):
            try:
                raw = json.loads(lark.JSON.marshal(data))
                message = self.parse_event_data(raw)
                if not message:
                    return
                on_message(message)
            except Exception as exc:
                logger.exception(f"handle lark ws event failed: {exc}")

        return (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(_handle_p2)
            .build()
        )

    def _extract_text_from_post(self, content: Dict[str, Any]) -> str:
        texts = []
        zh_cn = content.get("zh_cn", {})
        lines = zh_cn.get("content", [])
        for line in lines:
            if not isinstance(line, list):
                continue
            for item in line:
                if isinstance(item, dict) and item.get("tag") == "text":
                    texts.append(str(item.get("text", "")))
        return " ".join([t for t in texts if t])

    def _convert_response_to_lark_format(self, response: IMResponse) -> Dict[str, Any]:
        if response.content_type == "card_entity":
            try:
                card = json.loads(response.content)
            except Exception:
                card = self._build_fallback_card(response.content)
            if not isinstance(card, dict):
                card = self._build_fallback_card(response.content)
            return {"msg_type": "card_entity", "content": card}
        text = response.content
        if len(text) > self._max_message_length:
            text = text[: self._max_message_length - 20] + "\n... (消息过长已截断)"
        if response.content_type == "markdown":
            return {
                "msg_type": "post",
                "content": self._build_post_content(text),
            }
        return {"msg_type": "text", "content": {"text": text}}

    async def _send_card_entity(self, chat: IMChat, card_content: Dict[str, Any], response: IMResponse) -> Tuple[bool, Optional[str]]:
        card_content = self._sanitize_card_content(card_content)
        card_id: Optional[str] = None
        if self._card_entity_available:
            card_id = await self._create_card_entity(card_content)
        if card_id:
            payload = {"type": "card", "data": {"card_id": card_id}}
            return await self._send_raw_message(chat, "interactive", payload, response)
        fallback_payload = {"card": card_content}
        ok, message_id = await self._send_raw_message(chat, "interactive", fallback_payload, response)
        if ok:
            return ok, message_id
        fallback_text = self._extract_card_plain_text(card_content)
        return await self._send_raw_message(chat, "text", {"text": fallback_text}, response)

    async def _send_raw_message(
        self,
        chat: IMChat,
        msg_type: str,
        payload: Dict[str, Any],
        response: IMResponse,
    ) -> Tuple[bool, Optional[str]]:
        req_body_builder = lark.im.v1.CreateMessageRequestBody.builder()
        req_body_builder = self._apply_reply_context(req_body_builder, chat, response)
        req_body = req_body_builder.receive_id(chat.chat_id).msg_type(msg_type).content(json.dumps(payload, ensure_ascii=False)).build()
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(req_body)
            .build()
        )

        def _send():
            return self._client.im.v1.message.create(req)

        try:
            resp = await asyncio.to_thread(_send)
            if not resp.success():
                logger.error(f"send lark raw message failed: code={resp.code}, msg={resp.msg}")
                return False, None
            return True, self._extract_message_id(resp)
        except Exception as exc:
            logger.exception(f"send lark raw message exception: {exc}")
            return False, None

    async def _patch_raw_message(self, message_id: str, msg_type: str, payload: Any) -> bool:
        body_content = json.dumps(payload, ensure_ascii=False)
        req_variants = [
            ("PatchMessageRequestBody", "PatchMessageRequest", "patch"),
            ("UpdateMessageRequestBody", "UpdateMessageRequest", "update"),
        ]
        for body_name, req_name, method_name in req_variants:
            body_cls = getattr(lark.im.v1, body_name, None)
            req_cls = getattr(lark.im.v1, req_name, None)
            api_method = getattr(self._client.im.v1.message, method_name, None)
            if not body_cls or not req_cls or not api_method:
                continue
            try:
                req_body_builder = body_cls.builder()
                # Patch/Update 只改 content，不传 msg_type，否则飞书返回 230001 invalid msg_type
                if hasattr(req_body_builder, "content"):
                    req_body_builder.content(body_content)
                req_body = req_body_builder.build()
                req_builder = req_cls.builder()
                if hasattr(req_builder, "message_id"):
                    req_builder.message_id(message_id)
                req_builder.request_body(req_body)
                req = req_builder.build()
                resp = await asyncio.to_thread(api_method, req)
                if resp.success():
                    return True
                logger.warning(f"update lark message failed: code={resp.code}, msg={resp.msg}, method={method_name}")
            except Exception as exc:
                logger.warning(f"update lark message exception: {exc}, method={method_name}")
        return False

    def _apply_reply_context(self, req_body_builder: Any, chat: IMChat, response: IMResponse) -> Any:
        reply_to_message_id = response.reply_to_message_id or chat.root_id or chat.thread_id
        if not reply_to_message_id:
            return req_body_builder
        if hasattr(req_body_builder, "reply_to_message_id"):
            req_body_builder.reply_to_message_id(reply_to_message_id)
        if hasattr(req_body_builder, "reply_message_id"):
            req_body_builder.reply_message_id(reply_to_message_id)
        if hasattr(req_body_builder, "reply_in_thread"):
            req_body_builder.reply_in_thread(True)
        return req_body_builder

    def _extract_message_id(self, resp: Any) -> Optional[str]:
        data = getattr(resp, "data", None)
        if data is None:
            return None
        message_id = getattr(data, "message_id", None)
        if message_id:
            return str(message_id)
        return None

    async def _create_card_entity(self, card_content: Dict[str, Any]) -> Optional[str]:
        try:
            cardkit = getattr(self._client, "cardkit", None)
            if not cardkit:
                return None
            v1 = getattr(cardkit, "v1", None)
            card_api = getattr(v1, "card", None) if v1 else None
            create_api = getattr(card_api, "create", None) if card_api else None
            if create_api is None:
                return None
            normalized_card = self._sanitize_card_content(card_content)
            card_data = json.dumps(normalized_card, ensure_ascii=False, separators=(",", ":")).strip()
            if not card_data or card_data == "{}":
                logger.warning("create lark card entity skipped: empty card payload")
                return None

            def _create():
                req_body_builder = lark.cardkit.v1.CreateCardRequestBody.builder()
                req_body_builder.type("card_json")
                req_body_builder.data(card_data)
                req_body = req_body_builder.build()
                req = lark.cardkit.v1.CreateCardRequest.builder().request_body(req_body).build()
                return create_api(req)

            resp = await asyncio.to_thread(_create)
            if not resp or not resp.success():
                code = getattr(resp, "code", "unknown")
                msg = getattr(resp, "msg", "")
                if self._is_card_permission_error(code, msg):
                    self._card_entity_available = False
                    if not self._card_permission_warned:
                        logger.warning(f"lark card entity permission missing, auto downgrade to interactive card: code={code}, msg={msg}")
                        self._card_permission_warned = True
                if self._is_card_entity_payload_error(code, msg):
                    self._card_entity_available = False
                    logger.warning(f"lark card entity disabled due to invalid payload response: code={code}, msg={msg}")
                logger.warning(f"create lark card entity failed: code={code}, msg={msg}")
                return None
            data = getattr(resp, "data", None)
            return getattr(data, "card_id", None) if data else None
        except Exception as exc:
            logger.warning(f"create lark card entity exception: {exc}")
            return None

    def _sanitize_lark_md_content(self, content: str) -> str:
        """Sanitize text for lark_md to avoid Feishu 200621 parse card json err."""
        if not content:
            return ""
        s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(content))
        s = re.sub(r"```+", "'", s)
        s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)
        if len(s) > 4000:
            s = s[:3997] + "..."
        return s

    def _apply_lark_md_sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            if value.get("tag") == "lark_md" and "content" in value:
                return {k: (self._sanitize_lark_md_content(v) if k == "content" else self._apply_lark_md_sanitize(v)) for k, v in value.items()}
            return {k: self._apply_lark_md_sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._apply_lark_md_sanitize(v) for v in value]
        return value

    def _normalize_card_body(self, payload: Dict[str, Any]) -> None:
        """Ensure card uses body.elements (Feishu JSON 2.0)."""
        if "elements" in payload and "body" not in payload:
            payload["body"] = {"elements": payload.pop("elements")}
        if "body" not in payload:
            payload["body"] = {"elements": []}

    def _sanitize_card_content(self, card_content: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._clean_json_value(dict(card_content))
        self._normalize_card_body(payload)
        payload = self._apply_lark_md_sanitize(payload)
        payload.setdefault("config", {})
        payload["config"]["update_multi"] = True
        payload.setdefault("schema", "2.0")
        raw = json.dumps(payload, ensure_ascii=False)
        if len(raw.encode("utf-8")) <= 30 * 1024:
            return payload
        trimmed = {
            "schema": "2.0",
            "config": {"update_multi": True},
            "header": {
                "title": {"tag": "plain_text", "content": "ScienceClaw 处理中"},
                "template": "blue",
            },
            "body": {
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": "进度信息较长，已自动精简显示。"}},
                ],
            },
        }
        return trimmed

    def _build_fallback_card(self, text: str) -> Dict[str, Any]:
        content = text[:600]
        return {
            "schema": "2.0",
            "config": {"update_multi": True},
            "header": {
                "title": {"tag": "plain_text", "content": "ScienceClaw 任务进展"},
                "template": "blue",
            },
            "body": {
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": content}},
                ],
            },
        }

    def _is_card_permission_error(self, code: Any, msg: Any) -> bool:
        msg_text = str(msg or "").lower()
        return str(code) == "99991663" or "cardkit:card:write" in msg_text

    def _is_card_entity_payload_error(self, code: Any, msg: Any) -> bool:
        msg_text = str(msg or "").lower()
        code_text = str(code or "")
        if code_text in {"200610", "200621"}:
            return True
        return "body is nil" in msg_text or "parse card json err" in msg_text

    def _build_post_content(self, text: str) -> Dict[str, Any]:
        lines = str(text or "").splitlines()
        if not lines:
            lines = [""]
        content_lines = [[{"tag": "text", "text": line if line else " "}] for line in lines]
        return {
            "zh_cn": {
                "title": "",
                "content": content_lines,
            }
        }

    def _clean_json_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._clean_json_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._clean_json_value(v) for v in value]
        if isinstance(value, str):
            return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
        return value

    def _extract_card_plain_text(self, card_content: Dict[str, Any]) -> str:
        texts: list[str] = []
        header = card_content.get("header", {})
        title = header.get("title", {}) if isinstance(header, dict) else {}
        title_text = title.get("content") if isinstance(title, dict) else ""
        if title_text:
            texts.append(str(title_text))
        elements = (card_content.get("body") or {}).get("elements", card_content.get("elements", []))
        if not isinstance(elements, list):
            elements = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            text_block = element.get("text")
            if isinstance(text_block, dict):
                content = text_block.get("content")
                if content:
                    texts.append(str(content))
        if not texts:
            return "任务处理中..."
        joined = "\n".join(texts)
        if len(joined) > 1000:
            return joined[:980] + "\n..."
        return joined

class LarkMessageFormatter(IMMessageFormatter):
    platform = IMPlatform.LARK

    def format_thinking(self, content: str) -> str:
        if len(content) > 200:
            return f"💭 {content[:200]}..."
        return f"💭 {content}"

    def format_tool_call(self, function: str, args: dict) -> str:
        return f"🔧 正在使用 {function}"

    def format_tool_result(self, function: str, success: bool) -> str:
        icon = "✅" if success else "❌"
        return f"{icon} {function} 执行完成"

    def format_plan(self, steps: list) -> str:
        lines = ["📋 执行计划"]
        for step in steps:
            status = step.get("status", "pending")
            icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(status, "⏳")
            lines.append(f"{icon} {step.get('description', '')}")
        return "\n".join(lines)

    def format_error(self, error: str) -> str:
        return f"❌ 错误：{error}"

    def truncate_message(self, text: str, max_length: int = 4000) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 20] + "\n... (消息过长已截断)"

    def convert_to_platform_format(self, response: IMResponse) -> Dict[str, Any]:
        if response.content_type == "markdown":
            lines = str(response.content or "").splitlines()
            if not lines:
                lines = [""]
            content_lines = [[{"tag": "text", "text": line if line else " "}] for line in lines]
            return {
                "msg_type": "post",
                "content": {
                    "zh_cn": {
                        "title": "",
                        "content": content_lines,
                    }
                },
            }
        return {"msg_type": "text", "content": {"text": response.content}}
