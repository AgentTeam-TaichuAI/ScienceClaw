from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import Request
from loguru import logger

from backend.im.base import IMAdapter, IMAttachment, IMChat, IMMessage, IMMessageFormatter, IMPlatform, IMResponse, IMUser

_MAX_TELEGRAM_TEXT_LENGTH = 4096
_MAX_MEDIA_GROUP_SIZE = 10


class TelegramAdapter(IMAdapter):
    platform = IMPlatform.TELEGRAM
    PRIVATE_COMMANDS: List[Dict[str, str]] = [
        {"command": "start", "description": "开始使用并查看帮助"},
        {"command": "help", "description": "查看可用命令"},
        {"command": "new", "description": "新建当前会话"},
        {"command": "history", "description": "查看最近会话"},
        {"command": "status", "description": "查看当前状态"},
        {"command": "bind", "description": "查看绑定说明"},
        {"command": "unbind", "description": "查看解绑说明"},
    ]
    GROUP_COMMANDS: List[Dict[str, str]] = [
        {"command": "start", "description": "开始使用并查看帮助"},
        {"command": "help", "description": "查看可用命令"},
        {"command": "new", "description": "新建当前会话"},
        {"command": "status", "description": "查看当前状态"},
    ]

    def __init__(
        self,
        bot_token: str,
        webhook_secret: str = "",
        public_base_url: str = "",
        max_message_length: int = 4000,
    ):
        if not bot_token:
            raise RuntimeError("Telegram bot token is required")
        self.bot_token = bot_token
        self.webhook_secret = webhook_secret
        self.public_base_url = (public_base_url or "").rstrip("/")
        self._api_base = f"https://api.telegram.org/bot{bot_token}"
        self._file_base = f"https://api.telegram.org/file/bot{bot_token}"
        self._max_message_length = max(200, min(int(max_message_length), _MAX_TELEGRAM_TEXT_LENGTH))
        self._bot_id: Optional[int] = None
        self._bot_username: str = ""

    def get_webhook_path(self) -> str:
        return "/api/v1/im/webhook/telegram"

    async def verify_webhook(self, request: Request) -> bool:
        if not self.webhook_secret:
            return True
        return request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") == self.webhook_secret

    async def parse_message(self, request: Request) -> Optional[IMMessage]:
        try:
            payload = await request.json()
        except Exception as exc:
            logger.exception(f"parse telegram webhook payload failed: {exc}")
            return None
        return self.parse_update(payload)

    def parse_update(self, payload: Dict[str, Any]) -> Optional[IMMessage]:
        update_id = payload.get("update_id")
        message = payload.get("message")
        if not isinstance(message, dict):
            return None

        sender = message.get("from") or {}
        if sender.get("is_bot"):
            return None
        chat = message.get("chat") or {}
        chat_type_raw = str(chat.get("type") or "")
        chat_type = "p2p" if chat_type_raw == "private" else "group"

        text = str(message.get("text") or message.get("caption") or "")
        entities = list(message.get("entities") or []) + list(message.get("caption_entities") or [])
        is_reply_to_bot = self._is_reply_to_bot(message)
        is_at_me = chat_type == "p2p" or is_reply_to_bot or self._contains_bot_mention(text, entities)
        attachments = self._extract_attachments(message)
        content_type = "text" if "text" in message else (attachments[0].kind if attachments else "text")
        thread_id = self._stringify_optional(message.get("message_thread_id"))
        reply_to_message = message.get("reply_to_message") or {}
        root_id = self._stringify_optional(reply_to_message.get("message_id"))

        return IMMessage(
            platform=self.platform,
            message_id=str(message.get("message_id") or ""),
            delivery_id=str(update_id or message.get("message_id") or ""),
            user=IMUser(
                platform=self.platform,
                platform_user_id=str(sender.get("id") or ""),
                name=self._build_user_display_name(sender),
            ),
            chat=IMChat(
                platform=self.platform,
                chat_id=str(chat.get("id") or ""),
                chat_type=chat_type,
                name=str(chat.get("title") or chat.get("username") or ""),
                thread_id=thread_id,
                root_id=root_id,
            ),
            content_type=content_type,
            content=text,
            raw_message=payload,
            timestamp=int(message.get("date") or 0),
            is_at_me=is_at_me,
            attachments=attachments,
            media_group_id=self._stringify_optional(message.get("media_group_id")),
        )

    async def send_message(self, chat: IMChat, response: IMResponse) -> bool:
        ok, _ = await self.send_message_with_id(chat, response)
        return ok

    async def send_message_with_id(self, chat: IMChat, response: IMResponse) -> Tuple[bool, Optional[str]]:
        message_id: Optional[str] = None
        if response.content:
            message_id = await self._send_text_message(chat, response)
        elif not response.attachments:
            return False, None

        if response.attachments:
            sent_ids = await self.send_attachments(
                chat=chat,
                attachments=response.attachments,
                reply_to_message_id=response.reply_to_message_id,
                thread_id=response.thread_id,
            )
            if message_id is None and sent_ids:
                message_id = sent_ids[0]
        return True, message_id

    async def update_message(self, message_id: str, response: IMResponse) -> bool:
        chat_id, telegram_message_id = self._parse_edit_target(message_id)
        if not chat_id or not telegram_message_id:
            return False
        text = self._truncate_text(response.content)
        payload: Dict[str, Any] = {
            "chat_id": self._maybe_int(chat_id),
            "message_id": self._maybe_int(telegram_message_id),
            "text": text or ".",
            "disable_web_page_preview": True,
        }
        try:
            await self._api_request("editMessageText", json_body=payload)
            return True
        except Exception as exc:
            logger.warning(f"update telegram message failed: {exc}")
            return False

    async def send_typing_indicator(self, chat: IMChat) -> None:
        try:
            await self._api_request(
                "sendChatAction",
                json_body={
                    "chat_id": self._maybe_int(chat.chat_id),
                    "action": "typing",
                    **self._thread_context(chat=chat, thread_id=chat.thread_id),
                },
            )
        except Exception as exc:
            logger.debug(f"send telegram typing indicator failed: {exc}")

    async def handle_url_verification(self, request: Request) -> Optional[Dict[str, Any]]:
        return None

    async def get_me(self) -> Dict[str, Any]:
        data = await self._api_request("getMe")
        self._bot_id = int(data.get("id") or 0) or None
        self._bot_username = str(data.get("username") or "")
        return data

    async def sync_bot_commands(self) -> None:
        await self._api_request(
            "setMyCommands",
            json_body={
                "commands": self.PRIVATE_COMMANDS,
                "scope": {"type": "all_private_chats"},
            },
        )
        await self._api_request(
            "setMyCommands",
            json_body={
                "commands": self.GROUP_COMMANDS,
                "scope": {"type": "all_group_chats"},
            },
        )
        await self._api_request(
            "setChatMenuButton",
            json_body={
                "menu_button": {"type": "commands"},
            },
        )

    async def set_webhook(self) -> None:
        if not self.public_base_url:
            raise RuntimeError("telegram_public_base_url is required for webhook mode")
        payload: Dict[str, Any] = {
            "url": f"{self.public_base_url}{self.get_webhook_path()}",
            "allowed_updates": ["message"],
        }
        if self.webhook_secret:
            payload["secret_token"] = self.webhook_secret
        await self._api_request("setWebhook", json_body=payload)

    async def delete_webhook(self, drop_pending_updates: bool = False) -> None:
        await self._api_request(
            "deleteWebhook",
            json_body={"drop_pending_updates": bool(drop_pending_updates)},
        )

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "timeout": max(1, min(timeout, 60)),
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        data = await self._api_request("getUpdates", json_body=payload, timeout=timeout + 10)
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def download_message_attachments(self, message: IMMessage, target_dir: Path) -> List[IMAttachment]:
        target_dir.mkdir(parents=True, exist_ok=True)
        materialized: List[IMAttachment] = []
        for index, attachment in enumerate(message.attachments, start=1):
            file_id = str(attachment.metadata.get("telegram_file_id") or "")
            if not file_id:
                continue
            try:
                file_info = await self._api_request("getFile", json_body={"file_id": file_id})
                remote_path = str(file_info.get("file_path") or "")
                if not remote_path:
                    continue
                filename = self._ensure_filename(
                    attachment.filename or Path(remote_path).name,
                    fallback_prefix=f"{attachment.kind}_{message.message_id}_{index}",
                    mime_type=attachment.mime_type,
                )
                dest_path = self._unique_path(target_dir / filename)
                await self._download_file(remote_path, dest_path)
                materialized.append(
                    IMAttachment(
                        kind=attachment.kind,
                        file_path=str(dest_path),
                        filename=dest_path.name,
                        mime_type=attachment.mime_type,
                        caption=attachment.caption,
                        source_message_id=attachment.source_message_id,
                        metadata=dict(attachment.metadata),
                    )
                )
            except Exception as exc:
                logger.warning(f"download telegram attachment failed: message_id={message.message_id}, file_id={file_id}, error={exc}")
        return materialized

    async def send_attachments(
        self,
        chat: IMChat,
        attachments: List[IMAttachment],
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> List[str]:
        valid_attachments = [attachment for attachment in attachments if attachment.file_path]
        if not valid_attachments:
            return []
        if self._can_send_media_group(valid_attachments):
            return await self._send_media_group(
                chat=chat,
                attachments=valid_attachments,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )
        sent_ids: List[str] = []
        for attachment in valid_attachments:
            sent_id = await self._send_single_attachment(
                chat=chat,
                attachment=attachment,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )
            if sent_id:
                sent_ids.append(sent_id)
        return sent_ids

    async def _send_text_message(self, chat: IMChat, response: IMResponse) -> Optional[str]:
        payload: Dict[str, Any] = {
            "chat_id": self._maybe_int(chat.chat_id),
            "text": self._truncate_text(response.content),
            "disable_web_page_preview": True,
        }
        payload.update(self._thread_context(chat=chat, thread_id=response.thread_id or chat.thread_id))
        if response.reply_to_message_id:
            payload["reply_to_message_id"] = self._maybe_int(response.reply_to_message_id)
        data = await self._api_request("sendMessage", json_body=payload)
        return self._extract_sent_message_id(data)

    async def _send_single_attachment(
        self,
        chat: IMChat,
        attachment: IMAttachment,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Optional[str]:
        method_name = {
            "photo": "sendPhoto",
            "document": "sendDocument",
            "audio": "sendAudio",
            "voice": "sendVoice",
            "video": "sendVideo",
            "animation": "sendAnimation",
            "sticker": "sendSticker",
        }.get(attachment.kind, "sendDocument")
        file_field = {
            "photo": "photo",
            "document": "document",
            "audio": "audio",
            "voice": "voice",
            "video": "video",
            "animation": "animation",
            "sticker": "sticker",
        }.get(attachment.kind, "document")
        payload: Dict[str, Any] = {
            "chat_id": str(self._maybe_int(chat.chat_id)),
        }
        payload.update(self._thread_context(chat=chat, thread_id=thread_id or chat.thread_id, stringify=True))
        if reply_to_message_id:
            payload["reply_to_message_id"] = str(self._maybe_int(reply_to_message_id))
        if attachment.caption and attachment.kind != "sticker":
            payload["caption"] = attachment.caption[:1024]
        try:
            data = await self._api_request(
                method_name,
                data=payload,
                files={file_field: self._open_upload_file(attachment.file_path, attachment.filename, attachment.mime_type)},
            )
            return self._extract_sent_message_id(data)
        except Exception as exc:
            if attachment.kind != "sticker":
                raise
            logger.warning(f"send telegram sticker failed, fallback to document: {exc}")
            fallback = IMAttachment(
                kind="document",
                file_path=attachment.file_path,
                filename=attachment.filename,
                mime_type=attachment.mime_type,
                caption=attachment.caption,
                source_message_id=attachment.source_message_id,
                metadata=dict(attachment.metadata),
            )
            return await self._send_single_attachment(
                chat=chat,
                attachment=fallback,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )

    async def _send_media_group(
        self,
        chat: IMChat,
        attachments: List[IMAttachment],
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> List[str]:
        sent_ids: List[str] = []
        for start in range(0, len(attachments), _MAX_MEDIA_GROUP_SIZE):
            batch = attachments[start:start + _MAX_MEDIA_GROUP_SIZE]
            media_payload: List[Dict[str, Any]] = []
            files: List[Tuple[str, Tuple[str, Any, str]]] = []
            for index, attachment in enumerate(batch, start=1):
                attach_name = f"file{index}"
                media_item = {
                    "type": "photo" if attachment.kind == "photo" else "video",
                    "media": f"attach://{attach_name}",
                }
                if attachment.caption and index == 1:
                    media_item["caption"] = attachment.caption[:1024]
                media_payload.append(media_item)
                files.append(
                    (
                        attach_name,
                        self._open_upload_file(attachment.file_path, attachment.filename, attachment.mime_type),
                    )
                )
            data: Dict[str, Any] = {
                "chat_id": str(self._maybe_int(chat.chat_id)),
                "media": json.dumps(media_payload, ensure_ascii=False),
            }
            data.update(self._thread_context(chat=chat, thread_id=thread_id or chat.thread_id, stringify=True))
            result = await self._api_request("sendMediaGroup", data=data, files=files)
            if isinstance(result, list):
                sent_ids.extend([self._extract_sent_message_id(item) for item in result if self._extract_sent_message_id(item)])
        return sent_ids

    async def _api_request(
        self,
        method: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        timeout: int = 60,
    ) -> Any:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self._api_base}/{method}",
                    json=json_body,
                    data=data,
                    files=files,
                )
        finally:
            self._close_upload_files(files)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API {method} failed: {payload}")
        return payload.get("result")

    async def _download_file(self, remote_path: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(f"{self._file_base}/{remote_path}")
        response.raise_for_status()
        destination.write_bytes(response.content)

    def _extract_attachments(self, message: Dict[str, Any]) -> List[IMAttachment]:
        attachments: List[IMAttachment] = []
        caption = str(message.get("caption") or "")
        source_message_id = str(message.get("message_id") or "")

        if isinstance(message.get("photo"), list) and message["photo"]:
            photo_sizes = [item for item in message["photo"] if isinstance(item, dict)]
            photo = max(photo_sizes, key=lambda item: int(item.get("file_size") or 0))
            attachments.append(
                self._build_attachment(
                    kind="photo",
                    source=photo,
                    filename=f"photo_{source_message_id}.jpg",
                    mime_type="image/jpeg",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("document"), dict):
            document = message["document"]
            attachments.append(
                self._build_attachment(
                    kind="document",
                    source=document,
                    filename=str(document.get("file_name") or f"document_{source_message_id}"),
                    mime_type=document.get("mime_type"),
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("audio"), dict):
            audio = message["audio"]
            attachments.append(
                self._build_attachment(
                    kind="audio",
                    source=audio,
                    filename=str(audio.get("file_name") or f"audio_{source_message_id}.mp3"),
                    mime_type=audio.get("mime_type") or "audio/mpeg",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("voice"), dict):
            voice = message["voice"]
            attachments.append(
                self._build_attachment(
                    kind="voice",
                    source=voice,
                    filename=f"voice_{source_message_id}.ogg",
                    mime_type=voice.get("mime_type") or "audio/ogg",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("video"), dict):
            video = message["video"]
            attachments.append(
                self._build_attachment(
                    kind="video",
                    source=video,
                    filename=str(video.get("file_name") or f"video_{source_message_id}.mp4"),
                    mime_type=video.get("mime_type") or "video/mp4",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("animation"), dict):
            animation = message["animation"]
            attachments.append(
                self._build_attachment(
                    kind="animation",
                    source=animation,
                    filename=str(animation.get("file_name") or f"animation_{source_message_id}.gif"),
                    mime_type=animation.get("mime_type") or "image/gif",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        if isinstance(message.get("sticker"), dict):
            sticker = message["sticker"]
            ext = ".webp"
            if sticker.get("is_animated"):
                ext = ".tgs"
            elif sticker.get("is_video"):
                ext = ".webm"
            attachments.append(
                self._build_attachment(
                    kind="sticker",
                    source=sticker,
                    filename=f"sticker_{source_message_id}{ext}",
                    mime_type="application/octet-stream",
                    caption=caption,
                    source_message_id=source_message_id,
                )
            )
        return attachments

    def _build_attachment(
        self,
        *,
        kind: str,
        source: Dict[str, Any],
        filename: str,
        mime_type: Optional[str],
        caption: str,
        source_message_id: str,
    ) -> IMAttachment:
        return IMAttachment(
            kind=kind,
            file_path="",
            filename=filename,
            mime_type=str(mime_type or mimetypes.guess_type(filename)[0] or ""),
            caption=caption or None,
            source_message_id=source_message_id,
            metadata={
                "telegram_file_id": source.get("file_id"),
                "telegram_file_unique_id": source.get("file_unique_id"),
                "file_size": source.get("file_size"),
                "width": source.get("width"),
                "height": source.get("height"),
                "duration": source.get("duration"),
                "emoji": source.get("emoji"),
            },
        )

    def _contains_bot_mention(self, text: str, entities: List[Dict[str, Any]]) -> bool:
        if not text or not self._bot_username:
            return False
        lowered_username = f"@{self._bot_username.lower()}"
        for entity in entities:
            if str(entity.get("type") or "") != "mention":
                continue
            offset = int(entity.get("offset") or 0)
            length = int(entity.get("length") or 0)
            mention = text[offset:offset + length].lower()
            if mention == lowered_username:
                return True
        return False

    def _is_reply_to_bot(self, message: Dict[str, Any]) -> bool:
        reply = message.get("reply_to_message") or {}
        reply_from = reply.get("from") or {}
        if not reply_from.get("is_bot"):
            return False
        reply_bot_id = reply_from.get("id")
        if self._bot_id is not None and reply_bot_id == self._bot_id:
            return True
        reply_username = str(reply_from.get("username") or "").lower()
        return bool(self._bot_username and reply_username == self._bot_username.lower())

    def _build_user_display_name(self, sender: Dict[str, Any]) -> str:
        name_parts = [
            str(sender.get("first_name") or "").strip(),
            str(sender.get("last_name") or "").strip(),
        ]
        full_name = " ".join([part for part in name_parts if part]).strip()
        if full_name:
            return full_name
        return str(sender.get("username") or sender.get("id") or "")

    def _thread_context(self, chat: IMChat, thread_id: Optional[str], stringify: bool = False) -> Dict[str, Any]:
        resolved_thread_id = thread_id or chat.thread_id
        if not resolved_thread_id:
            return {}
        value = self._maybe_int(resolved_thread_id)
        return {"message_thread_id": str(value) if stringify else value}

    def _truncate_text(self, text: str) -> str:
        raw = str(text or "")
        if len(raw) <= self._max_message_length:
            return raw
        return raw[: self._max_message_length - 20] + "\n... (truncated)"

    def _parse_edit_target(self, message_id: str) -> Tuple[Optional[str], Optional[str]]:
        if ":" not in str(message_id or ""):
            return None, None
        chat_id, telegram_message_id = str(message_id).split(":", 1)
        return chat_id or None, telegram_message_id or None

    def _extract_sent_message_id(self, payload: Any) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        chat = payload.get("chat") or {}
        chat_id = chat.get("id")
        message_id = payload.get("message_id")
        if chat_id is None or message_id is None:
            return None
        return f"{chat_id}:{message_id}"

    def _can_send_media_group(self, attachments: List[IMAttachment]) -> bool:
        if not (2 <= len(attachments) <= _MAX_MEDIA_GROUP_SIZE):
            return False
        return all(attachment.kind in {"photo", "video"} for attachment in attachments)

    def _ensure_filename(self, filename: str, fallback_prefix: str, mime_type: Optional[str]) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "").strip("._")
        if normalized:
            return normalized
        suffix = mimetypes.guess_extension(mime_type or "") or ""
        return f"{fallback_prefix}{suffix}"

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        counter = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _open_upload_file(self, file_path: str, filename: str, mime_type: Optional[str]) -> Tuple[str, Any, str]:
        content_type = mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return filename, open(file_path, "rb"), content_type

    def _maybe_int(self, value: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return value

    def _stringify_optional(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    def _close_upload_files(self, files: Any) -> None:
        if isinstance(files, dict):
            iterable = files.values()
        elif isinstance(files, list):
            iterable = [item[1] for item in files if isinstance(item, tuple) and len(item) > 1]
        else:
            iterable = []
        for item in iterable:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            file_obj = item[1]
            try:
                file_obj.close()
            except Exception:
                continue


class TelegramMessageFormatter(IMMessageFormatter):
    platform = IMPlatform.TELEGRAM

    def format_thinking(self, content: str) -> str:
        text = str(content or "").strip()
        return text if len(text) <= 200 else text[:197] + "..."

    def format_tool_call(self, function: str, args: dict) -> str:
        return f"正在使用工具：{function}"

    def format_tool_result(self, function: str, success: bool) -> str:
        status = "完成" if success else "失败"
        return f"{function} 执行{status}"

    def format_plan(self, steps: list) -> str:
        lines = ["执行计划"]
        icon_map = {
            "pending": "[ ]",
            "in_progress": "[~]",
            "completed": "[x]",
            "failed": "[!]",
        }
        for step in steps:
            if not isinstance(step, dict):
                continue
            status = icon_map.get(str(step.get("status") or "pending"), "[ ]")
            description = str(step.get("description") or step.get("content") or "").strip()
            if description:
                lines.append(f"{status} {description}")
        return "\n".join(lines)

    def format_error(self, error: str) -> str:
        return f"执行出错：{error}"

    def truncate_message(self, text: str, max_length: int = 4000) -> str:
        raw = str(text or "")
        limit = max(200, min(int(max_length), _MAX_TELEGRAM_TEXT_LENGTH))
        if len(raw) <= limit:
            return raw
        return raw[: limit - 20] + "\n... (truncated)"

    def convert_to_platform_format(self, response: IMResponse) -> Dict[str, Any]:
        return {"text": self.truncate_message(response.content)}
