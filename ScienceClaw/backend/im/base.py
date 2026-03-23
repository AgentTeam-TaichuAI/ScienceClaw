from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class IMPlatform(Enum):
    LARK = "lark"
    WECOM = "wecom"
    DINGTALK = "dingtalk"
    SLACK = "slack"
    WECHAT = "wechat"


@dataclass
class IMUser:
    platform: IMPlatform
    platform_user_id: str
    platform_union_id: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None

    @property
    def unique_id(self) -> str:
        return f"{self.platform.value}:{self.platform_user_id}"


@dataclass
class IMChat:
    platform: IMPlatform
    chat_id: str
    chat_type: str
    name: Optional[str] = None
    thread_id: Optional[str] = None
    root_id: Optional[str] = None

    @property
    def unique_id(self) -> str:
        return f"{self.platform.value}:{self.chat_id}"


@dataclass
class IMMessage:
    platform: IMPlatform
    message_id: str
    user: IMUser
    chat: IMChat
    content_type: str
    content: str
    raw_message: Dict[str, Any]
    timestamp: int
    is_at_me: bool = False

    def get_text(self) -> str:
        if self.content_type == "text":
            return self.content
        return ""


@dataclass
class IMResponse:
    content_type: str
    content: str
    mentions: Optional[list] = None
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    root_id: Optional[str] = None


class IMAdapter(ABC):
    platform: IMPlatform

    @abstractmethod
    async def verify_webhook(self, request: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def parse_message(self, request: Any) -> Optional[IMMessage]:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, chat: IMChat, response: IMResponse) -> bool:
        raise NotImplementedError

    async def update_message(self, message_id: str, response: IMResponse) -> bool:
        return False

    @abstractmethod
    async def send_typing_indicator(self, chat: IMChat) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_webhook_path(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def handle_url_verification(self, request: Any) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class IMMessageFormatter(ABC):
    platform: IMPlatform

    @abstractmethod
    def format_thinking(self, content: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def format_tool_call(self, function: str, args: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def format_tool_result(self, function: str, success: bool) -> str:
        raise NotImplementedError

    @abstractmethod
    def format_plan(self, steps: list) -> str:
        raise NotImplementedError

    @abstractmethod
    def format_error(self, error: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def truncate_message(self, text: str, max_length: int = 4000) -> str:
        raise NotImplementedError

    @abstractmethod
    def convert_to_platform_format(self, response: IMResponse) -> Dict[str, Any]:
        raise NotImplementedError
