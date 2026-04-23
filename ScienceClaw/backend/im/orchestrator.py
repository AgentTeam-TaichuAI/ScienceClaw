from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from pymongo.errors import DuplicateKeyError

from backend.deepagent.runner import arun_science_task_stream
from backend.deepagent.sessions import ScienceSession, async_get_science_session
from backend.im.base import IMAdapter, IMAttachment, IMMessage, IMMessageFormatter, IMPlatform, IMResponse
from backend.im.command_handler import IMCommandHandler
from backend.im.session_manager import IMSessionManager
from backend.im.session_persistence import (
    maybe_generate_session_title,
    persist_assistant_message,
    persist_done_event,
    persist_error_message,
    persist_plan_event,
    persist_step_event,
    persist_thinking_event,
    persist_tool_call_event,
    persist_tool_result_event,
    persist_user_message,
)
from backend.im.user_binding import IMUserBindingManager
from backend.im.user_binding_service import IMUserBindingService
from backend.im.workspace_files import build_output_attachments, diff_workspace_files, snapshot_workspace_files
from backend.mongodb.db import db


class IMServiceOrchestrator:
    def __init__(
        self,
        progress_mode: str = "text_multi",
        progress_interval_ms: int = 1200,
        realtime_events: Optional[list[str]] = None,
        max_message_length: int = 4000,
        progress_detail_level: str = "detailed",
        telegram_send_output_files: bool = True,
    ):
        self.adapters: Dict[IMPlatform, IMAdapter] = {}
        self.formatters: Dict[IMPlatform, IMMessageFormatter] = {}
        self.session_manager = IMSessionManager()
        self.user_binding = IMUserBindingManager()
        self.user_binding_service = IMUserBindingService(self.user_binding)
        self.command_handler = IMCommandHandler(self.session_manager)
        self.message_dedup_collection = "im_message_dedup"
        self.progress_mode = progress_mode if progress_mode in ("text_multi", "card_entity") else "text_multi"
        self.progress_interval_ms = max(300, min(progress_interval_ms, 10000))
        allowed_events = {"plan_update", "planning_message", "tool_call", "tool_result", "error"}
        self.realtime_events = {evt for evt in (realtime_events or []) if evt in allowed_events}
        self.max_message_length = max(500, min(int(max_message_length), 20000))
        self.progress_detail_level = progress_detail_level if progress_detail_level in ("compact", "detailed") else "detailed"
        self.telegram_send_output_files = bool(telegram_send_output_files)
        self._media_group_buffer: Dict[str, List[IMMessage]] = {}
        self._media_group_tasks: Dict[str, asyncio.Task] = {}
        self._media_group_lock = asyncio.Lock()

    def register_adapter(self, platform: IMPlatform, adapter: IMAdapter, formatter: IMMessageFormatter) -> None:
        self.adapters[platform] = adapter
        self.formatters[platform] = formatter
        logger.info(f"registered im adapter: {platform.value}")

    async def handle_webhook(self, platform: IMPlatform, request: Any) -> Any:
        adapter = self.adapters.get(platform)
        if not adapter:
            raise HTTPException(status_code=503, detail=f"adapter not configured: {platform.value}")
        if not await adapter.verify_webhook(request):
            raise HTTPException(status_code=401, detail="invalid signature")
        verification_response = await adapter.handle_url_verification(request)
        if verification_response:
            return verification_response
        message = await adapter.parse_message(request)
        if not message:
            return {"code": 0, "msg": "ok"}
        accepted = await self._mark_message_once(message)
        if not accepted:
            return {"code": 0, "msg": "ok"}
        await self._dispatch_message(adapter, message)
        return {"code": 0, "msg": "ok"}

    async def handle_incoming_message(self, platform: IMPlatform, message: IMMessage) -> bool:
        adapter = self.adapters.get(platform)
        if not adapter:
            logger.error(f"adapter not configured: {platform.value}")
            return False
        accepted = await self._mark_message_once(message)
        if not accepted:
            logger.info(
                f"[IM] duplicate message ignored: platform={platform.value}, "
                f"delivery_id={message.delivery_id}, user={message.user.platform_user_id or '-'}"
            )
            return False
        logger.info(
            f"[IM] message accepted: platform={platform.value}, "
            f"message_id={message.message_id}, delivery_id={message.delivery_id}, "
            f"chat_id={message.chat.chat_id}, user={message.user.platform_user_id or '-'}"
        )
        await self._dispatch_message(adapter, message)
        return True

    async def _dispatch_message(self, adapter: IMAdapter, message: IMMessage) -> None:
        if message.platform == IMPlatform.TELEGRAM and message.media_group_id:
            await self._enqueue_media_group_message(adapter, message)
            return
        asyncio.create_task(self._process_message(adapter, message))

    async def _enqueue_media_group_message(self, adapter: IMAdapter, message: IMMessage) -> None:
        key = f"{message.platform.value}:{message.chat.chat_id}:{message.media_group_id}"
        async with self._media_group_lock:
            self._media_group_buffer.setdefault(key, []).append(message)
            current_task = self._media_group_tasks.get(key)
            if current_task and not current_task.done():
                return
            self._media_group_tasks[key] = asyncio.create_task(
                self._flush_media_group(adapter, key),
                name=f"telegram-media-group-{message.media_group_id}",
            )

    async def _flush_media_group(self, adapter: IMAdapter, key: str) -> None:
        await asyncio.sleep(1.2)
        async with self._media_group_lock:
            messages = self._media_group_buffer.pop(key, [])
            self._media_group_tasks.pop(key, None)
        if not messages:
            return
        merged = self._merge_media_group_messages(messages)
        await self._process_message(adapter, merged)

    def _merge_media_group_messages(self, messages: List[IMMessage]) -> IMMessage:
        ordered = sorted(messages, key=lambda item: (item.timestamp, int(item.message_id or "0")))
        first = ordered[0]
        merged_attachments: List[IMAttachment] = []
        content = ""
        for item in ordered:
            merged_attachments.extend(item.attachments)
            if not content and item.content:
                content = item.content
        if not content and merged_attachments:
            content = "请处理我刚上传的附件"
        return IMMessage(
            platform=first.platform,
            message_id=first.message_id,
            delivery_id=first.delivery_id,
            user=first.user,
            chat=first.chat,
            content_type=first.content_type if content else "text",
            content=content,
            raw_message=first.raw_message,
            timestamp=first.timestamp,
            is_at_me=first.is_at_me,
            attachments=merged_attachments,
            media_group_id=first.media_group_id,
        )

    def _start_typing_heartbeat(self, adapter: IMAdapter, chat: Any) -> Optional[asyncio.Task]:
        if adapter.platform != IMPlatform.TELEGRAM:
            return None
        return asyncio.create_task(
            self._typing_heartbeat(adapter, chat),
            name=f"im-typing-{adapter.platform.value}-{getattr(chat, 'chat_id', 'unknown')}",
        )

    async def _typing_heartbeat(self, adapter: IMAdapter, chat: Any, interval_seconds: float = 4.0) -> None:
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                await adapter.send_typing_indicator(chat)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug(f"typing heartbeat stopped unexpectedly: {exc}")

    async def _stop_background_task(self, task: Optional[asyncio.Task]) -> None:
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug(f"background task stop failed: {exc}")

    async def _mark_message_once(self, message: IMMessage) -> bool:
        dedup_key = message.delivery_id or message.message_id
        if not dedup_key:
            return True
        try:
            await db.get_collection(self.message_dedup_collection).insert_one(
                {
                    "_id": f"{message.platform.value}:{dedup_key}",
                    "platform": message.platform.value,
                    "delivery_id": dedup_key,
                    "message_id": message.message_id,
                    "created_at": message.timestamp or int(time.time()),
                }
            )
            return True
        except DuplicateKeyError:
            return False

    async def _process_message(self, adapter: IMAdapter, message: IMMessage) -> None:
        formatter = self.formatters[message.platform]
        text = self._build_query_text(message)
        science_session: Optional[ScienceSession] = None
        typing_task: Optional[asyncio.Task] = None
        if not text and not message.attachments:
            logger.info(f"[IM] empty message ignored: platform={message.platform.value}, message_id={message.message_id}")
            return
        if message.chat.chat_type == "group" and not message.is_at_me and not text.startswith("/"):
            logger.info(
                f"[IM] group message ignored without mention: platform={message.platform.value}, "
                f"message_id={message.message_id}, chat_id={message.chat.chat_id}"
            )
            return
        try:
            auto_bound_from_pending = False
            auto_bound_single_user = False
            binding = await self.user_binding.get_binding(
                platform=message.platform,
                platform_user_id=message.user.platform_user_id,
            )
            if not binding and message.platform == IMPlatform.TELEGRAM:
                binding = await self.user_binding_service.consume_telegram_start_binding(
                    raw_message=text,
                    telegram_user_id=message.user.platform_user_id,
                )
                if binding:
                    await adapter.send_message(
                        message.chat,
                        IMResponse(
                            content_type="text",
                            content=self._build_binding_success_notice(adapter, message.platform),
                            reply_to_message_id=message.message_id if message.chat.chat_type == "p2p" else None,
                            thread_id=message.chat.thread_id,
                        ),
                    )
                    return
                if not binding and message.chat.chat_type == "p2p":
                    binding = await self.user_binding_service.consume_single_pending_telegram_binding(
                        telegram_user_id=message.user.platform_user_id,
                    )
                    auto_bound_from_pending = binding is not None
                if not binding and message.chat.chat_type == "p2p":
                    binding = await self.user_binding_service.auto_bind_single_local_user_telegram(
                        telegram_user_id=message.user.platform_user_id,
                    )
                    auto_bound_single_user = binding is not None
            if not binding:
                logger.info(
                    f"[IM] no binding found: platform={message.platform.value}, "
                    f"user={message.user.platform_user_id or '-'}, message_id={message.message_id}"
                )
                await adapter.send_message(
                    message.chat,
                    self._create_binding_guide(
                        platform=message.platform,
                        platform_user_id=message.user.platform_user_id,
                    ),
                )
                return
            if auto_bound_from_pending:
                logger.info(
                    f"[IM] telegram auto-bound from pending session: "
                    f"user={message.user.platform_user_id or '-'}, science_user={binding.science_user_id}"
                )
                await adapter.send_message(
                    message.chat,
                    IMResponse(
                        content_type="text",
                        content=self._build_binding_success_notice(adapter, message.platform),
                        reply_to_message_id=message.message_id if message.chat.chat_type == "p2p" else None,
                        thread_id=message.chat.thread_id,
                    ),
                )
            if auto_bound_single_user:
                logger.info(
                    f"[IM] telegram auto-bound to the only local user: "
                    f"user={message.user.platform_user_id or '-'}, science_user={binding.science_user_id}"
                )
                await adapter.send_message(
                    message.chat,
                    IMResponse(
                        content_type="text",
                        content=self._build_binding_success_notice(adapter, message.platform),
                        reply_to_message_id=message.message_id if message.chat.chat_type == "p2p" else None,
                        thread_id=message.chat.thread_id,
                    ),
                )

            if text.startswith("/"):
                command_result = await self.command_handler.handle(
                    command=text,
                    message=message,
                    formatter=formatter,
                    science_user_id=binding.science_user_id,
                )
                if command_result.response:
                    command_result.response.thread_id = message.chat.thread_id
                    if message.chat.chat_type == "p2p":
                        command_result.response.reply_to_message_id = message.message_id
                    await adapter.send_message(message.chat, command_result.response)
                if command_result.should_stop:
                    return

            context = await self.session_manager.resolve_context(
                message=message,
                bound_science_user_id=binding.science_user_id,
            )
            await adapter.send_typing_indicator(message.chat)
            typing_task = self._start_typing_heartbeat(adapter, message.chat)
            session = await self.session_manager.get_or_create_session(
                platform=message.platform,
                conversation_scope_id=context.conversation_scope_id,
                platform_chat_id=context.platform_chat_id,
                user_id=context.science_user_id,
                session_mode=context.session_mode,
            )
            science_session = await async_get_science_session(session.science_session_id)
            pre_snapshot = snapshot_workspace_files(science_session.vm_root_dir)
            inbound_attachments = await self._materialize_attachments(
                adapter=adapter,
                message=message,
                science_session=science_session,
            )
            inbound_attachment_paths = [attachment.file_path for attachment in inbound_attachments if attachment.file_path]
            task_query = text or "请处理我刚上传的附件"
            task_query = text or "Please process the files I just uploaded."
            await persist_user_message(science_session, task_query, inbound_attachment_paths)
            await maybe_generate_session_title(science_session, task_query)
            task_intro = task_query if len(task_query) <= 120 else f"{task_query[:117]}..."
            reply_to = message.message_id if message.chat.chat_type == "p2p" else None
            thread_id = message.chat.thread_id

            progress_state: Dict[str, Any] = {
                "started_monotonic": time.monotonic(),
                "tool_call_count": 0,
                "tool_result_count": 0,
                "plan_update_count": 0,
                "planning_message_count": 0,
                "error_count": 0,
            }
            ack_response = IMResponse(
                content_type="text",
                content=f"已收到任务，正在处理...\n任务简介：{task_intro}",
                reply_to_message_id=reply_to,
                thread_id=thread_id,
            )
            ack_response.content = f"Task received. Processing now...\nSummary: {task_intro}"
            ack_sent, ack_message_id = await adapter.send_message_with_id(message.chat, ack_response)
            if ack_sent and ack_message_id and self._should_edit_text_progress(adapter):
                progress_state["progress_message_id"] = ack_message_id

            enabled_realtime_events = self._resolve_realtime_events(message.platform)
            on_progress = None
            if enabled_realtime_events:

                async def _on_progress(event_type: str, content: str, event_data: Optional[Dict[str, Any]] = None) -> None:
                    await self._send_progress_update(
                        adapter=adapter,
                        chat=message.chat,
                        progress_state=progress_state,
                        event_type=event_type,
                        content=content,
                        event_data=event_data or {},
                        reply_to_message_id=reply_to,
                        thread_id=thread_id,
                    )

                on_progress = _on_progress

            response_text = await self._execute_ai_task(
                session=science_session,
                query=task_query,
                attachments=inbound_attachment_paths,
                formatter=formatter,
                on_progress=on_progress,
                progress_state=progress_state,
                realtime_events=enabled_realtime_events,
            )
            post_snapshot = snapshot_workspace_files(science_session.vm_root_dir)
            changed_files = diff_workspace_files(
                pre=pre_snapshot,
                post=post_snapshot,
                workspace_dir=science_session.vm_root_dir,
                session_id=science_session.session_id,
            )
            output_attachments = build_output_attachments(changed_files)
            output_attachment_paths = [attachment.file_path for attachment in output_attachments if attachment.file_path]
            delivered_output_attachments = output_attachments
            if message.platform == IMPlatform.TELEGRAM and not self.telegram_send_output_files:
                delivered_output_attachments = []
            await persist_assistant_message(science_session, response_text, output_attachment_paths)
            await persist_done_event(
                science_session,
                statistics=self._build_persisted_statistics(progress_state),
                round_files=changed_files,
            )
            await self._stop_background_task(typing_task)
            typing_task = None
            await self._send_final_result(
                adapter=adapter,
                chat=message.chat,
                progress_state=progress_state,
                response_text=response_text,
                reply_to_message_id=reply_to,
                thread_id=thread_id,
                attachments=delivered_output_attachments,
            )
        except Exception as exc:
            logger.exception(f"process im message failed: {exc}")
            await self._stop_background_task(typing_task)
            typing_task = None
            if science_session is not None:
                await persist_error_message(science_session, str(exc))
            await adapter.send_message(
                message.chat,
                IMResponse(
                    content_type="text",
                    content="Sorry, something went wrong while handling your message. Please try again later.",
                    reply_to_message_id=message.message_id if message.chat.chat_type == "p2p" else None,
                    thread_id=message.chat.thread_id,
                ),
            )
        finally:
            await self._stop_background_task(typing_task)
            return
            await adapter.send_message(
                message.chat,
                IMResponse(
                    content_type="text",
                    content="抱歉，处理消息时出错，请稍后重试。",
                    reply_to_message_id=message.message_id if message.chat.chat_type == "p2p" else None,
                    thread_id=message.chat.thread_id,
                ),
            )

    async def _materialize_attachments(
        self,
        adapter: IMAdapter,
        message: IMMessage,
        science_session: ScienceSession,
    ) -> List[IMAttachment]:
        if not message.attachments:
            return []
        download_method = getattr(adapter, "download_message_attachments", None)
        if not callable(download_method):
            return message.attachments
        target_dir = science_session.vm_root_dir / "incoming" / message.platform.value / f"{int(time.time())}_{message.message_id}"
        downloaded = await download_method(message, target_dir)
        if downloaded:
            return downloaded
        return message.attachments

    def _build_persisted_statistics(self, progress_state: Dict[str, Any]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        tool_call_count = max(
            int(progress_state.get("tool_call_count", 0)),
            int(progress_state.get("statistics_tool_call_count", 0)),
        )
        if tool_call_count:
            stats["tool_call_count"] = tool_call_count
        tool_result_count = int(progress_state.get("tool_result_count", 0))
        if tool_result_count:
            stats["tool_result_count"] = tool_result_count
        plan_update_count = int(progress_state.get("plan_update_count", 0))
        if plan_update_count:
            stats["plan_update_count"] = plan_update_count
        planning_message_count = int(progress_state.get("planning_message_count", 0))
        if planning_message_count:
            stats["planning_message_count"] = planning_message_count
        error_count = int(progress_state.get("error_count", 0))
        if error_count:
            stats["error_count"] = error_count
        total_duration_ms = progress_state.get("total_duration_ms")
        if isinstance(total_duration_ms, (int, float)) and total_duration_ms >= 0:
            stats["total_duration_ms"] = float(total_duration_ms)
        return stats

    async def _execute_ai_task(
        self,
        session: ScienceSession,
        query: str,
        attachments: Optional[List[str]],
        formatter: IMMessageFormatter,
        on_progress=None,
        progress_state: Optional[Dict[str, Any]] = None,
        realtime_events: Optional[set[str]] = None,
    ) -> str:
        enabled_realtime_events = set(realtime_events or set())
        message_chunks: List[str] = []
        error_messages: List[str] = []
        last_tool_result: Optional[str] = None

        async for evt in arun_science_task_stream(session=session, query=query, attachments=attachments):
            event_type = evt.get("event")
            data = evt.get("data", {})
            self._record_progress_metrics(progress_state, event_type, data)
            if event_type == "thinking":
                content = data.get("content")
                if content:
                    await persist_thinking_event(session, str(content))
                continue
            if event_type in {"plan", "plan_update"}:
                await persist_plan_event(session, data.get("plan") or [])
                if on_progress and event_type in enabled_realtime_events:
                    plan_steps = data.get("plan", [])
                    text = formatter.format_plan(plan_steps) if plan_steps else "Execution plan updated."
                    await on_progress("plan_update", text, data)
                continue
            if event_type == "step_start":
                step = data.get("step") or {}
                await persist_step_event(
                    session,
                    step_id=str(step.get("id") or ""),
                    description=str(step.get("content") or ""),
                    status="running",
                )
                continue
            if event_type == "step_end":
                await persist_step_event(
                    session,
                    step_id=str(data.get("step_id") or ""),
                    description="",
                    status="completed",
                )
                continue
            if event_type == "tool_call":
                await persist_tool_call_event(session, data)
                if on_progress and event_type in enabled_realtime_events:
                    text = formatter.format_tool_call(data.get("function", ""), data.get("args", {}))
                    await on_progress("tool_call", text, data)
                continue
            if event_type == "tool_result":
                await persist_tool_result_event(session, data)
                content = data.get("content")
                if isinstance(content, (dict, list)):
                    last_tool_result = json.dumps(content, ensure_ascii=False, indent=2)
                else:
                    last_tool_result = str(content)
                if on_progress and event_type in enabled_realtime_events:
                    success = str(data.get("status", "success")).lower() != "error"
                    text = formatter.format_tool_result(data.get("function", ""), success=success)
                    await on_progress("tool_result", text, data)
                continue
            if event_type == "planning_message":
                content = data.get("content")
                if content:
                    message_chunks.append(str(content))
                    await persist_thinking_event(session, str(content))
                if on_progress and event_type in enabled_realtime_events and content:
                    await on_progress("planning_message", self._normalize_realtime_content("planning_message", str(content)), data)
                continue
            if event_type == "plan_update":
                if on_progress and event_type in enabled_realtime_events:
                    plan_steps = data.get("plan", [])
                    text = formatter.format_plan(plan_steps) if plan_steps else "执行计划已更新"
                    await on_progress("plan_update", text, data)
                continue
            if event_type == "message_chunk":
                content = data.get("content")
                if content:
                    message_chunks.append(str(content))
                continue
            if event_type == "error":
                error_text = formatter.format_error(data.get("message", "未知错误"))
                error_messages.append(error_text)
                if on_progress and event_type in enabled_realtime_events:
                    await on_progress("error", self._normalize_realtime_content("error", error_text), data)
                continue
            if event_type == "statistics":
                continue
        if message_chunks:
            return self._merge_message_chunks(message_chunks)
        if error_messages:
            return "\n\n".join(error_messages)
        if last_tool_result:
            return f"任务已完成，结果如下：\n{last_tool_result}"
        return "任务已完成。"

    async def _send_final_result(
        self,
        adapter: IMAdapter,
        chat: Any,
        progress_state: Dict[str, Any],
        response_text: str,
        reply_to_message_id: Optional[str],
        thread_id: Optional[str],
        attachments: List[IMAttachment],
    ) -> None:
        if self.progress_mode == "card_entity" and adapter.supports_card_entity:
            result_card = self._build_result_card(progress_state, response_text)
            await adapter.send_message(
                chat,
                IMResponse(
                    content_type="card_entity",
                    content=json.dumps(result_card, ensure_ascii=False),
                    reply_to_message_id=reply_to_message_id,
                    thread_id=thread_id,
                ),
            )
            if len(response_text) > 1600:
                await self._send_markdown_chunks(
                    adapter=adapter,
                    chat=chat,
                    content=response_text,
                    reply_to_message_id=reply_to_message_id,
                    thread_id=thread_id,
                )
        else:
            await self._send_markdown_chunks(
                adapter=adapter,
                chat=chat,
                content=response_text,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
                edit_target_id=str(progress_state.get("progress_message_id") or "") or None,
            )
        send_attachments = getattr(adapter, "send_attachments", None)
        if attachments and callable(send_attachments):
            await send_attachments(
                chat=chat,
                attachments=attachments,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )

    async def _send_progress_update(
        self,
        adapter: IMAdapter,
        chat: Any,
        progress_state: Dict[str, Any],
        event_type: str,
        content: str,
        event_data: Dict[str, Any],
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> None:
        now = time.monotonic()
        progress_state.setdefault("started_monotonic", now)
        progress_changed = self._apply_progress_step(progress_state, event_type, content, event_data)
        if not progress_changed:
            return
        progress_state["latest_step"] = content[:120]
        interval_seconds = self.progress_interval_ms / 1000
        last_push = float(progress_state.get("last_push_monotonic") or 0)
        if (
            self._should_throttle_event(event_type)
            and now - last_push < interval_seconds
            and not self._should_force_send(event_type, event_data)
        ):
            return
        progress_state["last_push_monotonic"] = now

        if self.progress_mode == "card_entity" and adapter.supports_card_entity:
            card_payload = self._build_progress_card(progress_state)
            response = IMResponse(
                content_type="card_entity",
                content=json.dumps(card_payload, ensure_ascii=False),
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )
            progress_message_id = str(progress_state.get("progress_message_id") or "")
            if progress_message_id:
                updated = await adapter.update_message(progress_message_id, response)
                if updated:
                    return
            ok, message_id = await adapter.send_message_with_id(chat, response)
            if ok and message_id:
                progress_state["progress_message_id"] = message_id
            return

        text_response = IMResponse(
            content_type="text",
            content=self._build_progress_text(progress_state) if self._should_edit_text_progress(adapter) else content,
            reply_to_message_id=reply_to_message_id,
            thread_id=thread_id,
        )
        if self._should_edit_text_progress(adapter):
            progress_message_id = str(progress_state.get("progress_message_id") or "")
            if progress_message_id:
                updated = await adapter.update_message(progress_message_id, text_response)
                if updated:
                    return
            ok, message_id = await adapter.send_message_with_id(chat, text_response)
            if ok and message_id:
                progress_state["progress_message_id"] = message_id
            return
        await adapter.send_message(chat, text_response)

    async def _send_markdown_chunks(
        self,
        adapter: IMAdapter,
        chat: Any,
        content: str,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        edit_target_id: Optional[str] = None,
    ) -> None:
        safe_chunk_length = max(500, self.max_message_length - 120)
        chunks = self._split_message_chunks(content, safe_chunk_length)
        for index, chunk in enumerate(chunks, start=1):
            response = IMResponse(
                content_type="markdown",
                content=chunk,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
            )
            if index == 1 and edit_target_id:
                updated = await adapter.update_message(edit_target_id, response)
                if updated:
                    continue
            await adapter.send_message(chat, response)

    def _build_query_text(self, message: IMMessage) -> str:
        text = message.get_text().strip()
        if text:
            return text
        if message.attachments:
            return "请处理我刚上传的附件"
        return ""

    def _should_edit_text_progress(self, adapter: IMAdapter) -> bool:
        return adapter.platform == IMPlatform.TELEGRAM

    def _resolve_realtime_events(self, platform: IMPlatform) -> set[str]:
        enabled = set(self.realtime_events)
        if platform == IMPlatform.TELEGRAM and enabled == {"plan_update"}:
            return {"plan_update", "planning_message", "tool_call", "tool_result", "error"}
        return enabled

    def _build_progress_text(self, progress_state: Dict[str, Any]) -> str:
        steps = list(progress_state.get("steps", []))
        lines: List[str] = ["Processing..."]
        latest_step = str(progress_state.get("latest_step") or "").strip()
        if latest_step:
            lines.append(f"Latest: {latest_step}")
        if steps:
            lines.append("")
            lines.append("Recent progress:")
            for step in steps[-6:]:
                status = str(step.get("status") or "pending")
                title = str(step.get("title") or "").strip() or "Working"
                detail = str(step.get("detail") or "").strip()
                icon = {
                    "pending": "[ ]",
                    "in_progress": "[~]",
                    "completed": "[x]",
                    "failed": "[!]",
                }.get(status, "[ ]")
                line = f"{icon} {title}"
                if detail and self.progress_detail_level == "detailed":
                    line = f"{line}: {detail[:140]}"
                lines.append(line)
        elapsed_text = self._resolve_elapsed_text(progress_state)
        if elapsed_text:
            lines.append("")
            lines.append(f"Elapsed: {elapsed_text}")
        return "\n".join(lines).strip()

    def _build_progress_card(self, progress_state: Dict[str, Any]) -> Dict[str, Any]:
        steps = progress_state.get("steps", [])
        step_lines: List[str] = []
        for step in steps[-8:]:
            icon = self._step_icon(str(step.get("status", "pending")))
            title = str(step.get("title", "")).strip() or "处理中"
            detail = str(step.get("detail", "")).strip()
            if detail:
                step_lines.append(f"{icon} {title}  \n{detail}")
            else:
                step_lines.append(f"{icon} {title}")
        step_content = "\n".join(step_lines) if step_lines else "正在初始化执行流程"
        return {
            "schema": "2.0",
            "config": {"update_multi": True},
            "body": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": step_content},
                    },
                ],
            },
        }

    def _build_result_card(self, progress_state: Dict[str, Any], result_text: str) -> Dict[str, Any]:
        tool_call_count = max(
            int(progress_state.get("tool_call_count", 0)),
            int(progress_state.get("statistics_tool_call_count", 0)),
        )
        tool_result_count = int(progress_state.get("tool_result_count", 0))
        plan_update_count = int(progress_state.get("plan_update_count", 0))
        planning_message_count = int(progress_state.get("planning_message_count", 0))
        error_count = int(progress_state.get("error_count", 0))
        steps = progress_state.get("steps", [])
        failed_count = sum(1 for step in steps if str(step.get("status", "")) == "failed")
        elapsed_seconds = self._resolve_elapsed_text(progress_state)
        preview = result_text if len(result_text) <= 1600 else "结果较长，已拆分为后续消息发送。"
        key_points = self._extract_key_points(result_text)
        failed_summary = self._build_failed_steps_summary(steps)
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**执行统计**\n"
                        f"- 工具调用：`{tool_call_count}` 次\n"
                        f"- 工具完成：`{tool_result_count}` 次\n"
                        f"- 计划更新：`{plan_update_count}` 次\n"
                        f"- 规划说明：`{planning_message_count}` 条\n"
                        f"- 错误事件：`{error_count}` 条\n"
                        f"- 失败步骤：`{failed_count}` 项\n"
                        f"- 总耗时：`{elapsed_seconds}`"
                    ),
                },
            },
        ]
        if key_points:
            elements.extend(
                [
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": f"**关键结论**\n{key_points}"}},
                ]
            )
        if failed_summary:
            elements.extend(
                [
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": f"**失败步骤摘要**\n{failed_summary}"}},
                ]
            )
        elements.extend(
            [
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**最终结果**\n{preview}"}},
            ]
        )
        return {
            "schema": "2.0",
            "config": {"update_multi": True},
            "body": {"elements": elements},
        }

    def _split_message_chunks(self, text: str, max_length: int) -> list[str]:
        raw = str(text or "")
        if not raw:
            return [""]
        limit = max(500, int(max_length))
        if len(raw) <= limit:
            return [raw]
        chunks: list[str] = []
        start = 0
        while start < len(raw):
            end = min(start + limit, len(raw))
            if end < len(raw):
                split_candidates = [
                    raw.rfind("\n\n", start, end),
                    raw.rfind("\n", start, end),
                ]
                for split_at in split_candidates:
                    if split_at > start + int(limit * 0.55):
                        end = split_at
                        break
            piece = raw[start:end]
            if piece.count("```") % 2 == 1 and end < len(raw):
                next_fence = raw.find("```", end)
                if next_fence != -1 and next_fence - start <= limit + 400:
                    end = next_fence + 3
                    piece = raw[start:end]
            piece = piece.rstrip("\n")
            if piece:
                chunks.append(piece)
            start = end
            while start < len(raw) and raw[start] == "\n":
                start += 1
        return chunks if chunks else [raw[:limit]]

    def _merge_message_chunks(self, chunks: list[str]) -> str:
        merged: list[str] = []
        for item in chunks:
            chunk = str(item or "")
            if not chunk.strip():
                continue
            if merged and merged[-1].strip() == chunk.strip():
                continue
            if not merged:
                merged.append(chunk)
                continue
            if merged[-1].endswith("\n") or chunk.startswith("\n"):
                merged[-1] = f"{merged[-1]}{chunk}"
            else:
                merged[-1] = f"{merged[-1]}\n\n{chunk}"
        if not merged:
            return ""
        return "".join(merged)

    def _extract_key_points(self, result_text: str) -> str:
        lines = [line.strip() for line in str(result_text or "").splitlines() if line.strip()]
        if not lines:
            return ""
        bullet_lines = [line for line in lines if line.startswith(("-", "*", "1.", "2.", "3."))]
        selected = bullet_lines[:3] if bullet_lines else lines[:3]
        normalized: List[str] = []
        for line in selected:
            if line.startswith(("-", "*")):
                normalized.append(line)
            else:
                normalized.append(f"- {line[:140]}")
        return "\n".join(normalized)

    def _build_failed_steps_summary(self, steps: list[Dict[str, Any]]) -> str:
        failed_steps = [step for step in steps if str(step.get("status", "")) == "failed"]
        if not failed_steps:
            return ""
        lines: List[str] = []
        for step in failed_steps[-5:]:
            title = str(step.get("title", "")).strip() or "失败步骤"
            detail = str(step.get("detail", "")).strip()
            if detail:
                lines.append(f"- {title}：{detail[:120]}")
            else:
                lines.append(f"- {title}")
        return "\n".join(lines)

    def _apply_progress_step(
        self,
        progress_state: Dict[str, Any],
        event_type: str,
        content: str,
        event_data: Dict[str, Any],
    ) -> bool:
        steps = progress_state.setdefault("steps", [])
        pending_tools = progress_state.setdefault("pending_tools", {})
        changed = False
        if event_type == "tool_call":
            function_name = str(event_data.get("function", "") or "tool")
            args = self._summarize_tool_args(event_data.get("args"))
            step = {
                "status": "in_progress",
                "title": f"工具调用：{function_name}",
                "detail": args if self.progress_detail_level == "detailed" else "",
                "started_monotonic": float(time.monotonic()),
            }
            steps.append(step)
            pending_tools.setdefault(function_name, []).append(step)
            changed = True
        elif event_type == "tool_result":
            function_name = str(event_data.get("function", "") or "tool")
            status = str(event_data.get("status", "success")).lower()
            step_status = "completed" if status != "error" else "failed"
            pending_steps = pending_tools.get(function_name) or []
            step = pending_steps.pop(0) if pending_steps else None
            if not pending_steps and function_name in pending_tools:
                pending_tools.pop(function_name, None)
            elapsed = None
            if step:
                started = float(step.get("started_monotonic") or 0)
                if started > 0:
                    elapsed = max(0.0, time.monotonic() - started)
            detail = self._summarize_tool_result(event_data, elapsed_seconds=elapsed)
            if step:
                step["status"] = step_status
                step["detail"] = detail
            else:
                steps.append({"status": step_status, "title": f"工具结果：{function_name}", "detail": detail})
            changed = True
        elif event_type == "planning_message":
            detail = content[:160] if self.progress_detail_level == "detailed" else ""
            steps.append({"status": "completed", "title": "规划说明", "detail": detail})
            changed = True
        elif event_type == "plan_update":
            plan_steps = event_data.get("plan")
            if not isinstance(plan_steps, list) or not plan_steps:
                return False
            plan_hash = str(hash(str(plan_steps)))
            last_hash = str(progress_state.get("last_plan_hash", ""))
            if plan_hash == last_hash:
                return False
            progress_state["last_plan_hash"] = plan_hash
            existing_plan_steps: Dict[str, Dict[str, Any]] = {}
            for step in steps:
                if str(step.get("source", "")) != "plan":
                    continue
                key = str(step.get("plan_step_key", "")).strip()
                if key:
                    existing_plan_steps[key] = step
            status_map = {
                "completed": "completed",
                "in_progress": "in_progress",
                "running": "in_progress",
                "failed": "failed",
                "pending": "pending",
            }
            for plan_step in plan_steps:
                if not isinstance(plan_step, dict):
                    continue
                title = str(plan_step.get("description") or plan_step.get("content") or "").strip()
                if not title:
                    continue
                step_id = str(plan_step.get("id") or "").strip()
                step_key = step_id or title
                mapped_status = status_map.get(str(plan_step.get("status") or "pending").strip().lower(), "pending")
                target = existing_plan_steps.get(step_key)
                if target:
                    target["status"] = mapped_status
                    target["title"] = title
                    target["detail"] = ""
                else:
                    steps.append(
                        {
                            "status": mapped_status,
                            "title": title,
                            "detail": "",
                            "source": "plan",
                            "plan_step_key": step_key,
                        }
                    )
                    changed = True
            changed = True
        elif event_type == "error":
            detail = content[:160] if self.progress_detail_level == "detailed" else ""
            steps.append({"status": "failed", "title": "执行错误", "detail": detail})
            changed = True
        if len(steps) > 12:
            del steps[:-12]
            changed = True
        return changed

    def _summarize_tool_args(self, args: Any) -> str:
        if args is None:
            return "参数：无"
        if isinstance(args, dict):
            keys = [str(key) for key in args.keys()][:4]
            if not keys:
                return "参数：无"
            return f"参数：{', '.join(keys)}"
        if isinstance(args, list):
            return f"参数：列表({len(args)})"
        return f"参数：{str(args)[:80]}"

    def _summarize_tool_result(self, event_data: Dict[str, Any], elapsed_seconds: Optional[float] = None) -> str:
        status = str(event_data.get("status", "success")).lower()
        summary = "成功" if status != "error" else "失败"
        duration_text = self._extract_duration_text(event_data, elapsed_seconds)
        if self.progress_detail_level != "detailed":
            return f"结果：{summary}"
        content = event_data.get("content")
        if isinstance(content, str) and content.strip():
            return f"结果：{summary}，{duration_text}，{content.strip()[:90]}"
        if isinstance(content, dict):
            return f"结果：{summary}，{duration_text}，返回字段 {len(content)} 个"
        if isinstance(content, list):
            return f"结果：{summary}，{duration_text}，返回列表 {len(content)} 项"
        return f"结果：{summary}，{duration_text}"

    def _extract_duration_text(self, event_data: Dict[str, Any], elapsed_seconds: Optional[float]) -> str:
        duration_candidates = [
            event_data.get("duration_ms"),
            event_data.get("cost_ms"),
            event_data.get("duration"),
        ]
        for candidate in duration_candidates:
            if isinstance(candidate, (int, float)):
                value = float(candidate)
                if candidate in {event_data.get("duration_ms"), event_data.get("cost_ms")}:
                    return f"耗时 {max(value, 0.0) / 1000:.1f}s"
                return f"耗时 {max(value, 0.0):.1f}s"
        if elapsed_seconds is not None:
            return f"耗时 {max(elapsed_seconds, 0.0):.1f}s"
        return "耗时 -"

    def _format_elapsed_seconds(self, elapsed_seconds: float) -> str:
        total = int(max(0, elapsed_seconds))
        minutes, seconds = divmod(total, 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _resolve_elapsed_text(self, progress_state: Dict[str, Any]) -> str:
        total_duration_ms = progress_state.get("total_duration_ms")
        if isinstance(total_duration_ms, (int, float)) and total_duration_ms >= 0:
            return self._format_elapsed_seconds(float(total_duration_ms) / 1000)
        started = float(progress_state.get("started_monotonic") or time.monotonic())
        return self._format_elapsed_seconds(max(0.0, time.monotonic() - started))

    def _record_progress_metrics(
        self,
        progress_state: Optional[Dict[str, Any]],
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        if progress_state is None:
            return
        if event_type == "tool_call":
            progress_state["tool_call_count"] = int(progress_state.get("tool_call_count", 0)) + 1
        elif event_type == "tool_result":
            progress_state["tool_result_count"] = int(progress_state.get("tool_result_count", 0)) + 1
        elif event_type == "plan_update":
            progress_state["plan_update_count"] = int(progress_state.get("plan_update_count", 0)) + 1
        elif event_type == "planning_message":
            progress_state["planning_message_count"] = int(progress_state.get("planning_message_count", 0)) + 1
        elif event_type == "error":
            progress_state["error_count"] = int(progress_state.get("error_count", 0)) + 1
        elif event_type == "statistics":
            tool_calls = event_data.get("tool_call_count")
            total_duration_ms = event_data.get("total_duration_ms")
            if isinstance(tool_calls, (int, float)):
                progress_state["statistics_tool_call_count"] = int(tool_calls)
            if isinstance(total_duration_ms, (int, float)):
                progress_state["total_duration_ms"] = float(total_duration_ms)

    def _should_force_send(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        if event_type == "error":
            return True
        if event_type != "plan_update":
            return False
        plan_steps = event_data.get("plan")
        if not isinstance(plan_steps, list) or not plan_steps:
            return False
        statuses = [str(step.get("status", "")) for step in plan_steps if isinstance(step, dict)]
        if not statuses:
            return False
        return all(status == "completed" for status in statuses)

    def _should_throttle_event(self, event_type: str) -> bool:
        return event_type in ("plan_update", "planning_message")

    def _normalize_realtime_content(self, event_type: str, content: str) -> str:
        text = str(content or "").strip()
        if not text:
            return ""
        if event_type == "planning_message":
            return text if len(text) <= 220 else text[:217] + "..."
        if event_type == "error":
            return text if len(text) <= 260 else text[:257] + "..."
        return text

    def _build_binding_success_notice(self, adapter: IMAdapter, platform: IMPlatform) -> str:
        if platform == IMPlatform.TELEGRAM:
            bot_username = str(getattr(adapter, "_bot_username", "") or "").strip()
            if bot_username:
                return f"已成功绑定当前机器人 @{bot_username}，现在可以直接聊天了。"
            return "已成功绑定当前机器人，现在可以直接聊天了。"
        return "账号已绑定成功，现在可以直接聊天了。"

    def _step_icon(self, status: str) -> str:
        return {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(status, "⏳")

    def _create_binding_guide(self, platform: IMPlatform, platform_user_id: str) -> IMResponse:
        platform_name = {
            IMPlatform.LARK: "Lark",
            IMPlatform.TELEGRAM: "Telegram",
            IMPlatform.WECOM: "WeCom",
            IMPlatform.DINGTALK: "DingTalk",
            IMPlatform.SLACK: "Slack",
        }.get(platform, platform.value)
        content_lines = [
            "Welcome to ScienceClaw.",
            "",
            f"Your {platform_name} account is not linked yet.",
            "If this is a single-user deployment, send another private message and we can bind automatically.",
            "You can also open Web Settings -> IM -> Account Binding to link explicitly.",
        ]
        if platform == IMPlatform.TELEGRAM:
            content_lines.extend(
                [
                    "",
                    "If the web binding page is open, just send any private message here and we will link automatically.",
                    "You can also use the Telegram button in the web page to open the bot directly.",
                    f"Telegram user id detected: `{platform_user_id}`",
                    "",
                    "Manual fallback:",
                    f"`/bind_telegram {platform_user_id}`",
                ]
            )
        return IMResponse(content_type="markdown", content="\n".join(content_lines))
        platform_name = {
            IMPlatform.LARK: "飞书",
            IMPlatform.TELEGRAM: "Telegram",
            IMPlatform.WECOM: "企业微信",
            IMPlatform.DINGTALK: "钉钉",
            IMPlatform.SLACK: "Slack",
        }.get(platform, platform.value)
        pair_cmd = f"/bind_{platform.value} {platform_user_id}"
        extra_tip = ""
        if platform == IMPlatform.TELEGRAM:
            extra_tip = "请先在 Telegram 中给机器人发送 /start，然后再回到 Web 设置页完成绑定。\n"
        content = (
            "欢迎使用 ScienceClaw\n\n"
            f"当前 {platform_name} 账号尚未绑定，请先到 Web 设置页完成绑定：\n"
            "我的 -> IM -> 账号绑定\n\n"
            f"{extra_tip}"
            f"你的 {platform_name} 用户 ID：`{platform_user_id}`\n"
            f"可直接粘贴配对命令：`{pair_cmd}`\n"
            "绑定完成后即可在 IM 中直接对话。"
        )
        return IMResponse(content_type="markdown", content=content)
