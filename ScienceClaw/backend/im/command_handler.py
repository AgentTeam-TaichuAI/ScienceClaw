from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.im.base import IMMessage, IMMessageFormatter, IMResponse
from backend.im.session_manager import IMSessionManager


@dataclass
class CommandResult:
    response: Optional[IMResponse] = None
    should_stop: bool = False


class IMCommandHandler:
    def __init__(self, session_manager: IMSessionManager):
        self.session_manager = session_manager

    async def handle(
        self,
        command: str,
        message: IMMessage,
        formatter: IMMessageFormatter,
        science_user_id: str,
    ) -> CommandResult:
        cmd = (command or "").strip().split()[0].lower()
        if cmd == "/start":
            cmd = "/help"
        if cmd == "/help":
            return CommandResult(
                response=IMResponse(
                    content_type="markdown",
                    content=(
                        "可用命令：\n"
                        "/help - 查看帮助\n"
                        "/new - 新建当前会话\n"
                        "/history - 最近会话\n"
                        "/status - 当前状态\n"
                        "/bind - 查看绑定说明\n"
                        "/unbind - 查看解绑说明"
                    ),
                ),
                should_stop=True,
            )

        if cmd == "/new":
            context = await self.session_manager.resolve_context(message=message, bound_science_user_id=science_user_id)
            created = await self.session_manager.create_new_session(
                platform=message.platform,
                conversation_scope_id=context.conversation_scope_id,
                platform_chat_id=context.platform_chat_id,
                user_id=context.science_user_id,
                session_mode=context.session_mode,
            )
            return CommandResult(
                response=IMResponse(
                    content_type="text",
                    content=f"已创建新会话：{created.science_session_id}",
                ),
                should_stop=True,
            )

        if cmd == "/history":
            sessions = await self.session_manager.list_recent_sessions(
                platform=message.platform,
                user_id=science_user_id,
                limit=5,
            )
            if not sessions:
                text = "暂无历史会话"
            else:
                text = "最近会话：\n" + "\n".join([f"- {s.science_session_id}" for s in sessions])
            return CommandResult(
                response=IMResponse(content_type="text", content=text),
                should_stop=True,
            )

        if cmd == "/status":
            context = await self.session_manager.resolve_context(message=message, bound_science_user_id=science_user_id)
            current = await self.session_manager.get_current_session(
                platform=message.platform,
                conversation_scope_id=context.conversation_scope_id,
                platform_chat_id=context.platform_chat_id,
                user_id=context.science_user_id,
                session_mode=context.session_mode,
            )
            if current:
                if context.session_mode == "shared_topic":
                    content = f"当前 Topic 会话：{current.science_session_id}"
                else:
                    content = f"当前会话：{current.science_session_id}"
            else:
                latest = await self.session_manager.get_latest_by_user(
                    platform=message.platform,
                    user_id=science_user_id,
                )
                content = "当前无活跃会话"
                if latest:
                    content = f"最近会话：{latest.science_session_id}"
            return CommandResult(
                response=IMResponse(content_type="text", content=content),
                should_stop=True,
            )

        if cmd == "/bind":
            return CommandResult(
                response=IMResponse(
                    content_type="text",
                    content="当前账号已绑定，可直接提问；若需要重新绑定，请到 Web 设置页查看绑定信息。",
                ),
                should_stop=True,
            )

        if cmd == "/unbind":
            return CommandResult(
                response=IMResponse(
                    content_type="text",
                    content="请到 Web 设置页执行解绑，或调用绑定管理接口。",
                ),
                should_stop=True,
            )

        return CommandResult(response=None, should_stop=False)
