"""Native Python WeChat bridge via ilink bot API.

Speaks the WeChat ilink bot protocol directly — no Node.js, no OpenClaw.
Handles QR login, long-poll message loop, AI task dispatch, and reply delivery.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import struct
import time
from typing import Optional

import httpx
import shortuuid
from loguru import logger

from backend.deepagent.runner import arun_science_task_stream
from backend.deepagent.sessions import async_get_science_session
from backend.im.base import IMPlatform
from backend.im.session_manager import IMSessionManager
from backend.im.user_binding import IMUserBindingManager
from backend.mongodb.db import db
from backend.notifications import publish as notify
from backend.route.sessions import (
    _map_science_stream_to_agent_event,
    _append_session_event,
)

WEIXIN_BASE_URL = "https://ilinkai.weixin.qq.com"
CHANNEL_VERSION = "scienceclaw-1.0.0"
BOT_TYPE = "3"

DEFAULT_POLL_TIMEOUT_MS = 35_000
MAX_CONSECUTIVE_FAILURES = 3
BACKOFF_DELAY_S = 30
RETRY_DELAY_S = 2
SESSION_EXPIRED_ERRCODE = -14
MAX_CONCURRENT_MESSAGES = 5

WECHAT_STATE_COLLECTION = "wechat_bridge_state"
WECHAT_STATE_DOC_ID = "default"


# ── Protocol helpers ──────────────────────────────────────────────────────────


def _random_wechat_uin() -> str:
    uint32 = struct.unpack(">I", os.urandom(4))[0]
    return base64.b64encode(str(uint32).encode()).decode()


def _build_headers(token: Optional[str] = None, body_bytes_len: int = 0) -> dict:
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_wechat_uin(),
    }
    if body_bytes_len:
        headers["Content-Length"] = str(body_bytes_len)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _extract_text(msg: dict) -> str:
    items = msg.get("item_list") or []
    for item in items:
        t = item.get("type", 0)
        if t == 1:  # TEXT
            text = (item.get("text_item") or {}).get("text", "")
            ref = item.get("ref_msg")
            if not ref:
                return text
            ref_item = ref.get("message_item")
            if ref_item and ref_item.get("type", 0) in (2, 3, 4, 5):
                return text
            parts = []
            if ref.get("title"):
                parts.append(ref["title"])
            if ref_item:
                nested = _extract_text({"item_list": [ref_item]})
                if nested:
                    parts.append(nested)
            return f"[引用: {' | '.join(parts)}]\n{text}" if parts else text
        if t == 3:  # VOICE with text
            voice_text = (item.get("voice_item") or {}).get("text")
            if voice_text:
                return voice_text
    return ""


_CODE_BLOCK = re.compile(r"```[^\n]*\n?([\s\S]*?)```")
_IMG_LINK = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\|(.+)\|$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_BOLD_U = re.compile(r"__(.+?)__")
_ITALIC_U = re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_INLINE_CODE = re.compile(r"`(.+?)`")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^>\s?", re.MULTILINE)
_HR = re.compile(r"^[-*_]{3,}$", re.MULTILINE)
_MULTI_BLANK = re.compile(r"\n{3,}")


def _strip_markdown(text: str) -> str:
    r = text
    r = _CODE_BLOCK.sub(lambda m: m.group(1).strip(), r)
    r = _IMG_LINK.sub("", r)
    r = _LINK.sub(r"\1", r)
    r = _TABLE_SEP.sub("", r)
    r = _TABLE_ROW.sub(lambda m: "  ".join(c.strip() for c in m.group(1).split("|")), r)
    r = _BOLD.sub(r"\1", r)
    r = _ITALIC.sub(r"\1", r)
    r = _BOLD_U.sub(r"\1", r)
    r = _ITALIC_U.sub(r"\1", r)
    r = _INLINE_CODE.sub(r"\1", r)
    r = _HEADING.sub("", r)
    r = _BLOCKQUOTE.sub("", r)
    r = _HR.sub("", r)
    r = _MULTI_BLANK.sub("\n\n", r)
    return r.strip()


# ── Bridge ────────────────────────────────────────────────────────────────────


class WeChatBridge:
    """Singleton service managing the full WeChat connection lifecycle."""

    _instance: Optional["WeChatBridge"] = None

    def __init__(self) -> None:
        self._status = "idle"
        self._qr_content: Optional[str] = None
        self._qr_image_cache: Optional[str] = None
        self._qr_code_id: Optional[str] = None
        self._bot_token: Optional[str] = None
        self._account_id: Optional[str] = None
        self._base_url = WEIXIN_BASE_URL
        self._monitor_task: Optional[asyncio.Task] = None
        self._login_poll_task: Optional[asyncio.Task] = None
        self._logs: list[str] = []
        self._error: Optional[str] = None
        self._started_at: Optional[float] = None
        self._get_updates_buf = ""
        self._abort_event = asyncio.Event()
        self._context_tokens: dict[str, str] = {}
        self._admin_user_id: Optional[str] = None
        self._session_mgr = IMSessionManager()
        self._binding_mgr = IMUserBindingManager()
        self._client: Optional[httpx.AsyncClient] = None
        self._msg_semaphore = asyncio.Semaphore(MAX_CONCURRENT_MESSAGES)

    @classmethod
    def get_instance(cls) -> "WeChatBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_running(self) -> bool:
        return self._status in ("connected", "qr_pending", "qr_scanned")

    # ── Logging ───────────────────────────────────────────────────────────

    def _append_log(self, line: str) -> None:
        self._logs.append(line)
        if len(self._logs) > 500:
            self._logs = self._logs[-300:]

    def _log(self, msg: str) -> None:
        self._append_log(f"[{time.strftime('%H:%M:%S')}] {msg}")
        logger.info(f"[WeChat] {msg}")

    def _log_err(self, msg: str) -> None:
        self._append_log(f"[{time.strftime('%H:%M:%S')}] ❌ {msg}")
        logger.error(f"[WeChat] {msg}")

    # ── HTTP client ───────────────────────────────────────────────────────

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        return self._client

    # ── State persistence (MongoDB) ───────────────────────────────────────

    async def _save_state(self) -> None:
        await db.get_collection(WECHAT_STATE_COLLECTION).update_one(
            {"_id": WECHAT_STATE_DOC_ID},
            {"$set": {
                "bot_token": self._bot_token,
                "account_id": self._account_id,
                "base_url": self._base_url,
                "get_updates_buf": self._get_updates_buf,
                "admin_user_id": self._admin_user_id,
                "updated_at": int(time.time()),
            }},
            upsert=True,
        )

    async def _load_state(self) -> bool:
        doc = await db.get_collection(WECHAT_STATE_COLLECTION).find_one(
            {"_id": WECHAT_STATE_DOC_ID}
        )
        if not doc or not doc.get("bot_token"):
            return False
        self._bot_token = doc["bot_token"]
        self._account_id = doc.get("account_id")
        self._base_url = doc.get("base_url") or WEIXIN_BASE_URL
        self._get_updates_buf = doc.get("get_updates_buf") or ""
        self._admin_user_id = doc.get("admin_user_id")
        return True

    async def _clear_state(self) -> None:
        await db.get_collection(WECHAT_STATE_COLLECTION).delete_one(
            {"_id": WECHAT_STATE_DOC_ID}
        )

    # ── QR code image ─────────────────────────────────────────────────────

    def _make_qr_image(self, content: str) -> Optional[str]:
        try:
            import qrcode
            import qrcode.image.svg

            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(content)
            qr.make(fit=True)
            img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
            buf = io.BytesIO()
            img.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/svg+xml;base64,{b64}"
        except ImportError:
            self._log("qrcode 包未安装，无法生成二维码图片")
            return None

    # ── QR Login ──────────────────────────────────────────────────────────

    async def start_login(self, admin_user_id: str) -> dict:
        if self._status == "connected":
            return {"status": "already_connected", "message": "微信已连接"}

        await self.stop()
        self._logs = []
        self._error = None
        self._admin_user_id = admin_user_id
        self._abort_event.clear()
        self._log("正在获取微信登录二维码...")

        try:
            resp = await self._http().get(
                f"{self._base_url}/ilink/bot/get_bot_qrcode",
                params={"bot_type": BOT_TYPE},
            )
            resp.raise_for_status()
            data = resp.json()
            self._qr_code_id = data.get("qrcode")
            self._qr_content = data.get("qrcode_img_content")

            if not self._qr_code_id or not self._qr_content:
                self._error = "服务器未返回有效二维码"
                self._status = "error"
                self._log_err(self._error)
                return {"status": "error", "error": self._error}

            self._qr_image_cache = self._make_qr_image(self._qr_content)
            self._status = "qr_pending"
            self._started_at = time.time()
            self._log("二维码已生成，请使用微信扫描")

            self._login_poll_task = asyncio.create_task(self._poll_login())

            return {
                "status": "qr_pending",
                "qr_content": self._qr_content,
                "qr_image": self._qr_image_cache,
            }
        except Exception as exc:
            self._error = f"获取二维码失败: {exc}"
            self._status = "error"
            self._log_err(self._error)
            return {"status": "error", "error": self._error}

    async def _poll_login(self) -> None:
        client = self._http()
        max_refreshes = 3
        refresh_count = 0
        deadline = time.time() + 480

        while not self._abort_event.is_set() and time.time() < deadline:
            try:
                resp = await client.get(
                    f"{self._base_url}/ilink/bot/get_qrcode_status",
                    params={"qrcode": self._qr_code_id},
                    headers={"iLink-App-ClientVersion": "1"},
                    timeout=40.0,
                )
                data = resp.json()
                status = data.get("status", "wait")

                if status == "wait":
                    continue

                if status == "scaned":
                    if self._status != "qr_scanned":
                        self._status = "qr_scanned"
                        self._log("👀 已扫码，请在微信上确认...")
                    continue

                if status == "expired":
                    refresh_count += 1
                    if refresh_count > max_refreshes:
                        self._error = "二维码多次过期，请重新开始"
                        self._status = "error"
                        self._log_err(self._error)
                        return
                    self._log(f"⏳ 二维码已过期，正在刷新 ({refresh_count}/{max_refreshes})...")
                    try:
                        qr_resp = await client.get(
                            f"{self._base_url}/ilink/bot/get_bot_qrcode",
                            params={"bot_type": BOT_TYPE},
                        )
                        qr_data = qr_resp.json()
                        self._qr_code_id = qr_data.get("qrcode")
                        self._qr_content = qr_data.get("qrcode_img_content")
                        self._qr_image_cache = self._make_qr_image(self._qr_content) if self._qr_content else None
                        self._status = "qr_pending"
                        self._log("🔄 新二维码已生成，请重新扫描")
                    except Exception as e:
                        self._error = f"刷新二维码失败: {e}"
                        self._status = "error"
                        self._log_err(self._error)
                        return
                    continue

                if status == "confirmed":
                    bot_token = data.get("bot_token")
                    ilink_bot_id = data.get("ilink_bot_id")
                    new_base_url = data.get("baseurl")

                    if not bot_token or not ilink_bot_id:
                        self._error = "登录失败：服务器未返回必要信息"
                        self._status = "error"
                        self._log_err(self._error)
                        return

                    self._bot_token = bot_token
                    self._account_id = ilink_bot_id
                    if new_base_url:
                        self._base_url = new_base_url

                    self._log(f"✅ 微信连接成功！")
                    await self._save_state()

                    self._status = "connected"
                    self._qr_content = None
                    self._qr_image_cache = None
                    self._monitor_task = asyncio.create_task(self._message_loop())
                    return

            except httpx.TimeoutException:
                continue
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self._log_err(f"登录轮询错误: {exc}")
                await asyncio.sleep(2)

        if not self._abort_event.is_set():
            self._error = "登录超时"
            self._status = "error"
            self._log_err("登录超时，请重新开始")

    # ── Message loop ──────────────────────────────────────────────────────

    async def _message_loop(self) -> None:
        self._log("消息监听已启动")
        client = self._http()
        consecutive_failures = 0
        poll_timeout = DEFAULT_POLL_TIMEOUT_MS

        while not self._abort_event.is_set():
            try:
                body = json.dumps({
                    "get_updates_buf": self._get_updates_buf,
                    "base_info": {"channel_version": CHANNEL_VERSION},
                })
                headers = _build_headers(self._bot_token, len(body.encode()))

                resp = await client.post(
                    f"{self._base_url}/ilink/bot/getupdates",
                    content=body,
                    headers=headers,
                    timeout=httpx.Timeout(poll_timeout / 1000 + 10, connect=10.0),
                )
                data = resp.json()

                if data.get("longpolling_timeout_ms"):
                    poll_timeout = data["longpolling_timeout_ms"]

                ret = data.get("ret", 0)
                errcode = data.get("errcode", 0)
                if ret != 0 or errcode != 0:
                    if errcode == SESSION_EXPIRED_ERRCODE or ret == SESSION_EXPIRED_ERRCODE:
                        self._log_err("会话已过期，需要重新扫码登录")
                        self._status = "error"
                        self._error = "会话已过期，请重新扫码登录"
                        await self._clear_state()
                        return

                    consecutive_failures += 1
                    self._log_err(
                        f"getUpdates 错误: ret={ret} errcode={errcode} "
                        f"({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                    )
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        consecutive_failures = 0
                        await asyncio.sleep(BACKOFF_DELAY_S)
                    else:
                        await asyncio.sleep(RETRY_DELAY_S)
                    continue

                consecutive_failures = 0

                new_buf = data.get("get_updates_buf")
                if new_buf:
                    self._get_updates_buf = new_buf
                    await self._save_state()

                for msg in data.get("msgs") or []:
                    asyncio.create_task(self._handle_message_safe(msg))

            except httpx.TimeoutException:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                consecutive_failures += 1
                self._log_err(f"getUpdates 异常: {exc} ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    consecutive_failures = 0
                    await asyncio.sleep(BACKOFF_DELAY_S)
                else:
                    await asyncio.sleep(RETRY_DELAY_S)

        self._log("消息监听已停止")

    async def _handle_message_safe(self, msg: dict) -> None:
        async with self._msg_semaphore:
            try:
                await self._process_message(msg)
            except Exception as exc:
                self._log_err(f"处理消息失败: {exc}")

    async def _process_message(self, msg: dict) -> None:
        from_user = msg.get("from_user_id", "")
        if not from_user:
            return

        text = _extract_text(msg)
        if not text.strip():
            return

        ctx_token = msg.get("context_token")
        if ctx_token:
            self._context_tokens[from_user] = ctx_token

        short_id = from_user[:8]
        preview = text[:50] + ("..." if len(text) > 50 else "")
        self._log(f"收到消息 from={short_id}...: {preview}")

        if not self._admin_user_id:
            self._log_err("未设置管理员用户，无法处理消息")
            return

        binding = await self._binding_mgr.get_binding(
            platform=IMPlatform.WECHAT,
            platform_user_id=from_user,
        )
        if not binding:
            binding = await self._binding_mgr.create_binding(
                platform=IMPlatform.WECHAT,
                platform_user_id=from_user,
                science_user_id=self._admin_user_id,
            )
            self._log(f"自动绑定微信用户 {short_id}... → admin")

        session = await self._session_mgr.get_or_create_session(
            platform=IMPlatform.WECHAT,
            platform_chat_id=from_user,
            user_id=binding.science_user_id,
        )

        await self._send_typing(from_user, ctx_token)

        try:
            sci_session = await async_get_science_session(session.science_session_id)

            now_ts = int(time.time())
            user_event = {
                "event": "message",
                "data": {
                    "event_id": shortuuid.uuid(),
                    "timestamp": now_ts,
                    "content": text,
                    "role": "user",
                    "attachments": [],
                },
            }
            _append_session_event(sci_session, user_event)
            sci_session.status = "running"
            await sci_session.save()
            notify("session_updated", {
                "session_id": session.science_session_id,
                "user_id": binding.science_user_id,
                "session_event": user_event,
            })

            reply_chunks: list[str] = []
            last_tool_result: Optional[str] = None
            _chunk_buffer: list[str] = []
            _notify_base = {
                "session_id": session.science_session_id,
                "user_id": binding.science_user_id,
            }

            def _emit_event(session_event: dict) -> None:
                """Push an individual event to web clients in real-time."""
                notify("session_updated", {
                    **_notify_base,
                    "session_event": session_event,
                })

            async for evt in arun_science_task_stream(session=sci_session, query=text):
                raw_ev = evt.get("event")
                raw_data = evt.get("data", {})

                if raw_ev in ("message_chunk", "planning_message"):
                    c = raw_data.get("content")
                    if c:
                        reply_chunks.append(str(c))
                elif raw_ev == "tool_result":
                    c = raw_data.get("content")
                    if isinstance(c, (dict, list)):
                        last_tool_result = json.dumps(c, ensure_ascii=False, indent=2)
                    elif c:
                        last_tool_result = str(c)

                mapped = _map_science_stream_to_agent_event(evt)
                if mapped is None:
                    continue
                evt_name = mapped.get("event")
                if evt_name == "statistics":
                    continue

                if evt_name == "message_chunk":
                    _chunk_buffer.append(mapped.get("data", {}).get("content", ""))
                    _emit_event(mapped)
                    continue

                if evt_name == "message_chunk_done":
                    _emit_event(mapped)
                    if _chunk_buffer:
                        full_content = "".join(_chunk_buffer)
                        persist_msg = {
                            "event": "message",
                            "data": {
                                "event_id": shortuuid.uuid(),
                                "timestamp": int(time.time()),
                                "content": full_content,
                                "role": "assistant",
                                "attachments": [],
                            },
                        }
                        _append_session_event(sci_session, persist_msg)
                        await sci_session.save()
                        _chunk_buffer.clear()
                    continue

                _append_session_event(sci_session, mapped)
                if evt_name in ("message", "tool", "step", "plan"):
                    await sci_session.save()
                _emit_event(mapped)

            if reply_chunks:
                full = _merge_chunks(reply_chunks)
            elif last_tool_result:
                full = f"任务已完成。结果如下：\n{last_tool_result}"
            else:
                full = "任务已完成。"

            done_event = {
                "event": "done",
                "data": {
                    "event_id": shortuuid.uuid(),
                    "timestamp": int(time.time()),
                    "status": "completed",
                    "statistics": {},
                    "round_files": [],
                },
            }
            _append_session_event(sci_session, done_event)
            sci_session.status = "completed"
            sci_session.latest_message = full[:200]
            sci_session.latest_message_at = int(time.time())
            if not sci_session.title:
                sci_session.title = text[:50]
            await sci_session.save()
            _emit_event(done_event)

            plain = _strip_markdown(full)
            parts = _split_text(plain, 4000)
            for part in parts:
                await self._send_text(from_user, part, ctx_token)
                if len(parts) > 1:
                    await asyncio.sleep(0.5)

            self._log(f"回复已发送 to={short_id}..., 长度={len(plain)}")
        except Exception as exc:
            self._log_err(f"AI 任务执行失败: {exc}")
            await self._send_text(from_user, "抱歉，处理消息时出错，请稍后重试。", ctx_token)

    # ── Outbound ──────────────────────────────────────────────────────────

    async def _send_text(self, to: str, text: str, context_token: Optional[str] = None) -> None:
        ct = context_token or self._context_tokens.get(to)
        if not ct:
            self._log_err(f"无 context_token，无法发送到 {to[:8]}...")
            return

        body = json.dumps({
            "msg": {
                "from_user_id": "",
                "to_user_id": to,
                "client_id": f"sc-{shortuuid.uuid()}",
                "message_type": 2,
                "message_state": 2,
                "item_list": [{"type": 1, "text_item": {"text": text}}] if text else None,
                "context_token": ct,
            },
            "base_info": {"channel_version": CHANNEL_VERSION},
        })
        headers = _build_headers(self._bot_token, len(body.encode()))
        try:
            resp = await self._http().post(
                f"{self._base_url}/ilink/bot/sendmessage",
                content=body,
                headers=headers,
                timeout=15.0,
            )
            if resp.status_code != 200:
                self._log_err(f"发送消息失败: HTTP {resp.status_code}")
        except Exception as exc:
            self._log_err(f"发送消息异常: {exc}")

    async def _send_typing(self, to: str, context_token: Optional[str] = None) -> None:
        ct = context_token or self._context_tokens.get(to)
        try:
            cfg_body = json.dumps({
                "ilink_user_id": to,
                "context_token": ct,
                "base_info": {"channel_version": CHANNEL_VERSION},
            })
            headers = _build_headers(self._bot_token, len(cfg_body.encode()))
            resp = await self._http().post(
                f"{self._base_url}/ilink/bot/getconfig",
                content=cfg_body,
                headers=headers,
                timeout=5.0,
            )
            ticket = resp.json().get("typing_ticket")
            if not ticket:
                return

            typing_body = json.dumps({
                "ilink_user_id": to,
                "typing_ticket": ticket,
                "status": 1,
                "base_info": {"channel_version": CHANNEL_VERSION},
            })
            headers = _build_headers(self._bot_token, len(typing_body.encode()))
            await self._http().post(
                f"{self._base_url}/ilink/bot/sendtyping",
                content=typing_body,
                headers=headers,
                timeout=5.0,
            )
        except Exception:
            pass

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start_with_saved_token(self, admin_user_id: Optional[str] = None) -> dict:
        has_state = await self._load_state()
        if not has_state:
            return {"status": "no_saved_token", "message": "没有保存的 token，需要扫码登录"}

        if admin_user_id:
            self._admin_user_id = admin_user_id

        self._log("尝试使用保存的 token 恢复连接...")
        self._status = "connected"
        self._started_at = time.time()
        self._abort_event.clear()
        self._monitor_task = asyncio.create_task(self._message_loop())
        return {"status": "connected", "message": "已使用保存的 token 恢复连接"}

    async def stop(self) -> dict:
        self._abort_event.set()

        for task in (self._login_poll_task, self._monitor_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._login_poll_task = None
        self._monitor_task = None

        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

        was_running = self.is_running
        self._status = "idle"
        self._qr_content = None
        self._qr_image_cache = None
        self._qr_code_id = None

        if was_running:
            self._log("WeChat bridge 已停止")

        return {"status": "stopped"}

    async def logout(self) -> dict:
        await self.stop()
        await self._clear_state()
        self._bot_token = None
        self._account_id = None
        self._get_updates_buf = ""
        self._log("已登出并清除保存的凭据")
        return {"status": "logged_out"}

    def get_status(self, output_offset: int = 0) -> dict:
        total = len(self._logs)
        offset = max(0, min(output_offset, total))
        is_login = self._status in ("qr_pending", "qr_scanned")

        return {
            "status": self._status,
            "is_running": self._status == "connected",
            "is_logging_in": is_login,
            "error": self._error,
            "started_at": self._started_at,
            "qr_content": self._qr_content if is_login else None,
            "qr_image": self._qr_image_cache if is_login else None,
            "account_id": self._account_id,
            "has_saved_token": self._bot_token is not None,
            "output_total": total,
            "output_offset": offset,
            "output": self._logs[offset:],
        }


# ── Text helpers (module-level for testability) ───────────────────────────────


def _merge_chunks(chunks: list[str]) -> str:
    merged: list[str] = []
    for c in chunks:
        s = str(c or "").strip()
        if not s:
            continue
        if merged and merged[-1] == s:
            continue
        merged.append(s)
    return "\n\n".join(merged) if merged else ""


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        if end < len(text):
            for sep in ("\n\n", "\n", "。", ".", " "):
                pos = text.rfind(sep, start, end)
                if pos > start + max_len // 2:
                    end = pos + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            parts.append(chunk)
        start = end
    return parts or [text[:max_len]]
