from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import shortuuid

from backend.deepagent.sessions import async_create_science_session, async_get_science_session
from backend.im.base import IMPlatform
from backend.mongodb.db import db
from backend.notifications import publish as notify


@dataclass
class IMChatSession:
    id: str
    platform: IMPlatform
    platform_chat_id: str
    science_user_id: str
    science_session_id: str
    created_at: int
    updated_at: int
    status: str = "active"


class IMChatSessionRepo:
    def __init__(self):
        self.collection_name = "im_chat_sessions"

    async def get_active_session(
        self,
        platform: IMPlatform,
        platform_chat_id: str,
        user_id: str,
    ) -> Optional[IMChatSession]:
        doc = await db.get_collection(self.collection_name).find_one(
            {
                "platform": platform.value,
                "platform_chat_id": platform_chat_id,
                "science_user_id": user_id,
                "status": "active",
            },
            sort=[("updated_at", -1)],
        )
        if not doc:
            return None
        return self._doc_to_model(doc)

    async def add_session(self, session: IMChatSession) -> None:
        await db.get_collection(self.collection_name).insert_one(
            {
                "_id": session.id,
                "platform": session.platform.value,
                "platform_chat_id": session.platform_chat_id,
                "science_user_id": session.science_user_id,
                "science_session_id": session.science_session_id,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "status": session.status,
            }
        )

    async def touch_session(self, session_id: str, updated_at: int) -> None:
        await db.get_collection(self.collection_name).update_one(
            {"_id": session_id},
            {"$set": {"updated_at": updated_at}},
        )

    async def get_latest_by_user(self, platform: IMPlatform, user_id: str) -> Optional[IMChatSession]:
        doc = await db.get_collection(self.collection_name).find_one(
            {"platform": platform.value, "science_user_id": user_id, "status": "active"},
            sort=[("updated_at", -1)],
        )
        if not doc:
            return None
        return self._doc_to_model(doc)

    async def list_recent_sessions(
        self,
        platform: IMPlatform,
        user_id: str,
        limit: int = 5,
    ) -> List[IMChatSession]:
        cursor = (
            db.get_collection(self.collection_name)
            .find({"platform": platform.value, "science_user_id": user_id, "status": "active"})
            .sort("updated_at", -1)
            .limit(limit)
        )
        result: List[IMChatSession] = []
        async for doc in cursor:
            result.append(self._doc_to_model(doc))
        return result

    async def close_session(self, session_id: str) -> None:
        await db.get_collection(self.collection_name).update_one(
            {"_id": session_id},
            {"$set": {"status": "closed", "updated_at": int(time.time())}},
        )

    def _doc_to_model(self, doc: dict) -> IMChatSession:
        return IMChatSession(
            id=doc["_id"],
            platform=IMPlatform(doc["platform"]),
            platform_chat_id=doc["platform_chat_id"],
            science_user_id=doc["science_user_id"],
            science_session_id=doc["science_session_id"],
            created_at=int(doc.get("created_at", 0)),
            updated_at=int(doc.get("updated_at", 0)),
            status=doc.get("status", "active"),
        )


class IMUserCurrentModelConfigRepo:
    def __init__(self):
        self.collection_name = "sessions"

    async def get_latest_model_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        doc = await db.get_collection(self.collection_name).find_one(
            {
                "user_id": user_id,
                "model_config": {"$exists": True, "$ne": None},
            },
            projection={"model_config": 1},
            sort=[("updated_at", -1)],
        )
        model_config = (doc or {}).get("model_config")
        if not isinstance(model_config, dict):
            return None
        return deepcopy(model_config)


class IMUserCurrentModelConfigService:
    def __init__(self, model_config_repo: Optional[IMUserCurrentModelConfigRepo] = None):
        self.model_config_repo = model_config_repo or IMUserCurrentModelConfigRepo()

    async def get_current_model_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        return await self.model_config_repo.get_latest_model_config(user_id)


class IMSessionManager:
    def __init__(
        self,
        session_repo: Optional[IMChatSessionRepo] = None,
        model_config_service: Optional[IMUserCurrentModelConfigService] = None,
    ):
        self.session_repo = session_repo or IMChatSessionRepo()
        self.model_config_service = model_config_service or IMUserCurrentModelConfigService()

    async def get_or_create_session(
        self,
        platform: IMPlatform,
        platform_chat_id: str,
        user_id: str,
    ) -> IMChatSession:
        existing = await self.session_repo.get_active_session(
            platform=platform,
            platform_chat_id=platform_chat_id,
            user_id=user_id,
        )
        if existing:
            existing.updated_at = int(time.time())
            await self.session_repo.touch_session(existing.id, updated_at=existing.updated_at)
            await self._backfill_source(existing.science_session_id, platform)
            return existing
        return await self.create_new_session(platform=platform, platform_chat_id=platform_chat_id, user_id=user_id)

    async def _backfill_source(self, science_session_id: str, platform: IMPlatform) -> None:
        """Ensure the linked ScienceSession has `source` and pinned state set."""
        try:
            sci = await async_get_science_session(science_session_id)
            changed = False
            if not sci.source:
                sci.source = platform.value
                changed = True
            if platform == IMPlatform.WECHAT and not sci.pinned:
                sci.pinned = True
                changed = True
            if changed:
                await sci.save()
        except Exception:
            pass

    async def create_new_session(
        self,
        platform: IMPlatform,
        platform_chat_id: str,
        user_id: str,
    ) -> IMChatSession:
        model_config = await self.model_config_service.get_current_model_config(user_id)
        science_session = await async_create_science_session(
            mode="deep",
            user_id=user_id,
            model_config=model_config,
            source=platform.value,
        )
        if platform == IMPlatform.WECHAT:
            science_session.pinned = True
            await science_session.save()
        now = int(time.time())
        im_session = IMChatSession(
            id=shortuuid.uuid(),
            platform=platform,
            platform_chat_id=platform_chat_id,
            science_user_id=user_id,
            science_session_id=science_session.session_id,
            created_at=now,
            updated_at=now,
        )
        await self.session_repo.add_session(im_session)
        notify("session_created", {
            "session_id": science_session.session_id,
            "user_id": user_id,
            "source": platform.value,
        })
        return im_session

    async def get_latest_by_user(self, platform: IMPlatform, user_id: str) -> Optional[IMChatSession]:
        return await self.session_repo.get_latest_by_user(platform=platform, user_id=user_id)

    async def list_recent_sessions(
        self,
        platform: IMPlatform,
        user_id: str,
        limit: int = 5,
    ) -> List[IMChatSession]:
        return await self.session_repo.list_recent_sessions(
            platform=platform,
            user_id=user_id,
            limit=limit,
        )

    async def close_session(self, session_id: str) -> None:
        await self.session_repo.close_session(session_id)
