from __future__ import annotations

import re
from typing import Optional

from backend.im.base import IMPlatform
from backend.im.binding_tokens import IMBindingToken, IMBindingTokenManager
from backend.im.user_binding import IMUserBinding, IMUserBindingManager
from backend.mongodb.db import db

_LARK_BIND_COMMAND_RE = re.compile(r"^/bind_lark\s+([A-Za-z0-9_-]+)$", re.IGNORECASE)
_LARK_OPEN_ID_RE = re.compile(r"^ou_[A-Za-z0-9_-]+$")
_TELEGRAM_BIND_COMMAND_RE = re.compile(r"^/bind_telegram\s+([0-9]+)$", re.IGNORECASE)
_TELEGRAM_USER_ID_RE = re.compile(r"^[0-9]{4,32}$")
_TELEGRAM_START_BIND_RE = re.compile(r"^/start(?:@[A-Za-z0-9_]+)?\s+bind_([A-Za-z0-9_-]{8,64})$", re.IGNORECASE)


class IMUserBindingService:
    def __init__(
        self,
        binding_repo: Optional[IMUserBindingManager] = None,
        binding_token_repo: Optional[IMBindingTokenManager] = None,
    ):
        self.binding_repo = binding_repo or IMUserBindingManager()
        self.binding_token_repo = binding_token_repo or IMBindingTokenManager()

    def normalize_lark_user_id(self, raw_user_input: str) -> str:
        user_input = (raw_user_input or "").strip().strip("`")
        if not user_input:
            raise ValueError("飞书用户 ID 不能为空")

        bind_command_match = _LARK_BIND_COMMAND_RE.match(user_input)
        if bind_command_match:
            user_input = bind_command_match.group(1)

        if not _LARK_OPEN_ID_RE.match(user_input):
            raise ValueError("请输入飞书 open_id，或粘贴机器人返回的 /bind_lark ou_xxx 配对命令")
        return user_input

    def normalize_telegram_user_id(self, raw_user_input: str) -> str:
        user_input = (raw_user_input or "").strip().strip("`")
        if not user_input:
            raise ValueError("Telegram user id 不能为空")

        bind_command_match = _TELEGRAM_BIND_COMMAND_RE.match(user_input)
        if bind_command_match:
            user_input = bind_command_match.group(1)

        if not _TELEGRAM_USER_ID_RE.match(user_input):
            raise ValueError("请输入 Telegram user id，或粘贴机器人返回的 /bind_telegram 123456789 配对命令")
        return user_input

    def normalize_platform_user_id(self, platform: IMPlatform, raw_user_input: str) -> str:
        if platform == IMPlatform.LARK:
            return self.normalize_lark_user_id(raw_user_input)
        if platform == IMPlatform.TELEGRAM:
            return self.normalize_telegram_user_id(raw_user_input)
        user_input = (raw_user_input or "").strip().strip("`")
        if not user_input:
            raise ValueError(f"{platform.value} user id 不能为空")
        return user_input

    async def bind_user(
        self,
        platform: IMPlatform,
        science_user_id: str,
        raw_platform_user_id: str,
        platform_union_id: Optional[str] = None,
    ) -> IMUserBinding:
        platform_user_id = self.normalize_platform_user_id(platform, raw_platform_user_id)
        return await self.binding_repo.create_binding(
            platform=platform,
            platform_user_id=platform_user_id,
            platform_union_id=platform_union_id,
            science_user_id=science_user_id,
        )

    async def bind_lark_user(
        self,
        science_user_id: str,
        raw_lark_user_id: str,
        lark_union_id: Optional[str] = None,
    ) -> IMUserBinding:
        return await self.bind_user(
            platform=IMPlatform.LARK,
            science_user_id=science_user_id,
            raw_platform_user_id=raw_lark_user_id,
            platform_union_id=lark_union_id,
        )

    async def bind_telegram_user(self, science_user_id: str, raw_telegram_user_id: str) -> IMUserBinding:
        return await self.bind_user(
            platform=IMPlatform.TELEGRAM,
            science_user_id=science_user_id,
            raw_platform_user_id=raw_telegram_user_id,
        )

    def extract_telegram_start_bind_token(self, raw_message: str) -> Optional[str]:
        text = (raw_message or "").strip()
        if not text:
            return None
        match = _TELEGRAM_START_BIND_RE.match(text)
        if not match:
            return None
        return match.group(1)

    async def create_telegram_binding_token(
        self,
        science_user_id: str,
        ttl_seconds: int = 600,
    ) -> IMBindingToken:
        return await self.binding_token_repo.create_or_refresh_token(
            platform=IMPlatform.TELEGRAM,
            science_user_id=science_user_id,
            ttl_seconds=ttl_seconds,
        )

    async def consume_telegram_start_binding(
        self,
        raw_message: str,
        telegram_user_id: str,
    ) -> Optional[IMUserBinding]:
        token = self.extract_telegram_start_bind_token(raw_message)
        if not token:
            return None
        binding_token = await self.binding_token_repo.consume_token(
            platform=IMPlatform.TELEGRAM,
            token=token,
            platform_user_id=self.normalize_telegram_user_id(telegram_user_id),
        )
        if not binding_token:
            return None
        return await self.binding_repo.create_binding(
            platform=IMPlatform.TELEGRAM,
            platform_user_id=self.normalize_telegram_user_id(telegram_user_id),
            science_user_id=binding_token.science_user_id,
        )

    async def consume_single_pending_telegram_binding(
        self,
        telegram_user_id: str,
    ) -> Optional[IMUserBinding]:
        binding_token = await self.binding_token_repo.consume_single_pending_token(
            platform=IMPlatform.TELEGRAM,
            platform_user_id=self.normalize_telegram_user_id(telegram_user_id),
        )
        if not binding_token:
            return None
        return await self.binding_repo.create_binding(
            platform=IMPlatform.TELEGRAM,
            platform_user_id=self.normalize_telegram_user_id(telegram_user_id),
            science_user_id=binding_token.science_user_id,
        )

    async def auto_bind_single_local_user_telegram(
        self,
        telegram_user_id: str,
    ) -> Optional[IMUserBinding]:
        active_binding = await db.get_collection(self.binding_repo.collection_name).find_one(
            {
                "platform": IMPlatform.TELEGRAM.value,
                "status": "active",
            }
        )
        if active_binding:
            return None

        users = await db.get_collection("users").find(
            {},
            projection={"_id": 1},
        ).limit(2).to_list(length=2)
        if len(users) != 1:
            return None

        science_user_id = str(users[0]["_id"])
        return await self.binding_repo.create_binding(
            platform=IMPlatform.TELEGRAM,
            platform_user_id=self.normalize_telegram_user_id(telegram_user_id),
            science_user_id=science_user_id,
        )

    async def get_binding_status(self, platform: IMPlatform, science_user_id: str) -> Optional[IMUserBinding]:
        return await self.binding_repo.get_binding_by_science_user(
            platform=platform,
            science_user_id=science_user_id,
        )

    async def get_lark_binding_status(self, science_user_id: str) -> Optional[IMUserBinding]:
        return await self.get_binding_status(IMPlatform.LARK, science_user_id)

    async def get_telegram_binding_status(self, science_user_id: str) -> Optional[IMUserBinding]:
        return await self.get_binding_status(IMPlatform.TELEGRAM, science_user_id)

    async def unbind_user(self, platform: IMPlatform, science_user_id: str) -> bool:
        return await self.binding_repo.remove_binding_by_science_user(
            platform=platform,
            science_user_id=science_user_id,
        )

    async def unbind_lark_user(self, science_user_id: str) -> bool:
        return await self.unbind_user(IMPlatform.LARK, science_user_id)

    async def unbind_telegram_user(self, science_user_id: str) -> bool:
        return await self.unbind_user(IMPlatform.TELEGRAM, science_user_id)
