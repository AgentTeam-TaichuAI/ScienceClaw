from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import shortuuid

from backend.deepagent.sessions import async_create_science_session, async_get_science_session
from backend.im.base import IMChat, IMMessage, IMPlatform
from backend.mongodb.db import db
from backend.notifications import publish as notify


@dataclass
class IMChatSession:
    id: str
    platform: IMPlatform
    platform_chat_id: str
    conversation_scope_id: str
    session_mode: str
    science_user_id: str
    science_session_id: str
    created_at: int
    updated_at: int
    status: str = "active"


@dataclass
class IMConversationBinding:
    id: str
    platform: IMPlatform
    conversation_scope_id: str
    owner_science_user_id: str
    created_at: int
    updated_at: int
    status: str = "active"


@dataclass
class IMSessionContext:
    science_user_id: str
    conversation_scope_id: str
    session_mode: str
    platform_chat_id: str


class IMChatSessionRepo:
    def __init__(self):
        self.collection_name = "im_chat_sessions"

    async def get_active_session(
        self,
        platform: IMPlatform,
        conversation_scope_id: str,
        platform_chat_id: str,
        user_id: str,
        session_mode: str,
    ) -> Optional[IMChatSession]:
        collection = db.get_collection(self.collection_name)
        doc = await collection.find_one(
            {
                "platform": platform.value,
                "conversation_scope_id": conversation_scope_id,
                "science_user_id": user_id,
                "session_mode": session_mode,
                "status": "active",
            },
            sort=[("updated_at", -1)],
        )
        if doc:
            return self._doc_to_model(doc)

        # Backward-compatibility for pre-scope Lark sessions.
        legacy_doc = await collection.find_one(
            {
                "platform": platform.value,
                "platform_chat_id": platform_chat_id,
                "science_user_id": user_id,
                "status": "active",
            },
            sort=[("updated_at", -1)],
        )
        if legacy_doc:
            return self._doc_to_model(legacy_doc)
        return None

    async def add_session(self, session: IMChatSession) -> None:
        await db.get_collection(self.collection_name).insert_one(
            {
                "_id": session.id,
                "platform": session.platform.value,
                "platform_chat_id": session.platform_chat_id,
                "conversation_scope_id": session.conversation_scope_id,
                "session_mode": session.session_mode,
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
        conversation_scope_id = str(doc.get("conversation_scope_id") or "")
        platform_chat_id = str(doc.get("platform_chat_id") or "")
        if not conversation_scope_id and platform_chat_id:
            conversation_scope_id = f"{doc['platform']}:chat:{platform_chat_id}"
        return IMChatSession(
            id=doc["_id"],
            platform=IMPlatform(doc["platform"]),
            platform_chat_id=platform_chat_id,
            conversation_scope_id=conversation_scope_id,
            session_mode=str(doc.get("session_mode") or "per_user"),
            science_user_id=doc["science_user_id"],
            science_session_id=doc["science_session_id"],
            created_at=int(doc.get("created_at", 0)),
            updated_at=int(doc.get("updated_at", 0)),
            status=doc.get("status", "active"),
        )


class IMConversationBindingRepo:
    def __init__(self):
        self.collection_name = "im_conversation_bindings"

    async def get_active_binding(
        self,
        platform: IMPlatform,
        conversation_scope_id: str,
    ) -> Optional[IMConversationBinding]:
        doc = await db.get_collection(self.collection_name).find_one(
            {
                "platform": platform.value,
                "conversation_scope_id": conversation_scope_id,
                "status": "active",
            }
        )
        if not doc:
            return None
        return self._doc_to_model(doc)

    async def claim_owner(
        self,
        platform: IMPlatform,
        conversation_scope_id: str,
        owner_science_user_id: str,
    ) -> IMConversationBinding:
        now = int(time.time())
        collection = db.get_collection(self.collection_name)
        existing = await collection.find_one(
            {
                "platform": platform.value,
                "conversation_scope_id": conversation_scope_id,
            }
        )
        if existing:
            await collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "owner_science_user_id": owner_science_user_id,
                        "updated_at": now,
                        "status": "active",
                    }
                },
            )
            updated = await collection.find_one({"_id": existing["_id"]})
            return self._doc_to_model(updated)

        binding = IMConversationBinding(
            id=shortuuid.uuid(),
            platform=platform,
            conversation_scope_id=conversation_scope_id,
            owner_science_user_id=owner_science_user_id,
            created_at=now,
            updated_at=now,
        )
        await collection.insert_one(
            {
                "_id": binding.id,
                "platform": binding.platform.value,
                "conversation_scope_id": binding.conversation_scope_id,
                "owner_science_user_id": binding.owner_science_user_id,
                "created_at": binding.created_at,
                "updated_at": binding.updated_at,
                "status": binding.status,
            }
        )
        return binding

    async def release_by_owner(self, platform: IMPlatform, science_user_id: str) -> int:
        result = await db.get_collection(self.collection_name).update_many(
            {
                "platform": platform.value,
                "owner_science_user_id": science_user_id,
                "status": "active",
            },
            {"$set": {"status": "inactive", "updated_at": int(time.time())}},
        )
        return int(result.modified_count or 0)

    def _doc_to_model(self, doc: dict) -> IMConversationBinding:
        return IMConversationBinding(
            id=doc["_id"],
            platform=IMPlatform(doc["platform"]),
            conversation_scope_id=str(doc["conversation_scope_id"]),
            owner_science_user_id=str(doc["owner_science_user_id"]),
            created_at=int(doc.get("created_at", 0)),
            updated_at=int(doc.get("updated_at", 0)),
            status=str(doc.get("status") or "active"),
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
        conversation_binding_repo: Optional[IMConversationBindingRepo] = None,
        model_config_service: Optional[IMUserCurrentModelConfigService] = None,
    ):
        self.session_repo = session_repo or IMChatSessionRepo()
        self.conversation_binding_repo = conversation_binding_repo or IMConversationBindingRepo()
        self.model_config_service = model_config_service or IMUserCurrentModelConfigService()

    def build_conversation_scope_id(self, platform: IMPlatform, chat: IMChat) -> str:
        if platform == IMPlatform.TELEGRAM and chat.chat_type == "group" and chat.thread_id:
            return f"{platform.value}:chat:{chat.chat_id}:topic:{chat.thread_id}"
        return f"{platform.value}:chat:{chat.chat_id}"

    async def resolve_context(
        self,
        message: IMMessage,
        bound_science_user_id: str,
    ) -> IMSessionContext:
        platform_chat_id = str(message.chat.chat_id)
        conversation_scope_id = self.build_conversation_scope_id(message.platform, message.chat)
        if message.platform == IMPlatform.TELEGRAM and message.chat.chat_type == "group" and message.chat.thread_id:
            owner_binding = await self.conversation_binding_repo.get_active_binding(
                platform=message.platform,
                conversation_scope_id=conversation_scope_id,
            )
            if owner_binding is None:
                owner_binding = await self.conversation_binding_repo.claim_owner(
                    platform=message.platform,
                    conversation_scope_id=conversation_scope_id,
                    owner_science_user_id=bound_science_user_id,
                )
            return IMSessionContext(
                science_user_id=owner_binding.owner_science_user_id,
                conversation_scope_id=conversation_scope_id,
                session_mode="shared_topic",
                platform_chat_id=platform_chat_id,
            )
        return IMSessionContext(
            science_user_id=bound_science_user_id,
            conversation_scope_id=conversation_scope_id,
            session_mode="per_user",
            platform_chat_id=platform_chat_id,
        )

    async def get_or_create_session(
        self,
        platform: IMPlatform,
        conversation_scope_id: str,
        platform_chat_id: str,
        user_id: str,
        session_mode: str = "per_user",
    ) -> IMChatSession:
        existing = await self.session_repo.get_active_session(
            platform=platform,
            conversation_scope_id=conversation_scope_id,
            platform_chat_id=platform_chat_id,
            user_id=user_id,
            session_mode=session_mode,
        )
        if existing:
            try:
                await async_get_science_session(existing.science_session_id)
            except Exception:
                await self.session_repo.close_session(existing.id)
                return await self.create_new_session(
                    platform=platform, platform_chat_id=platform_chat_id, user_id=user_id,
                )
            existing.updated_at = int(time.time())
            await self.session_repo.touch_session(existing.id, updated_at=existing.updated_at)
            await self._backfill_source(existing.science_session_id, platform)
            return existing
        return await self.create_new_session(
            platform=platform,
            conversation_scope_id=conversation_scope_id,
            platform_chat_id=platform_chat_id,
            user_id=user_id,
            session_mode=session_mode,
        )

    async def get_current_session(
        self,
        platform: IMPlatform,
        conversation_scope_id: str,
        platform_chat_id: str,
        user_id: str,
        session_mode: str = "per_user",
    ) -> Optional[IMChatSession]:
        return await self.session_repo.get_active_session(
            platform=platform,
            conversation_scope_id=conversation_scope_id,
            platform_chat_id=platform_chat_id,
            user_id=user_id,
            session_mode=session_mode,
        )

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
        conversation_scope_id: str,
        platform_chat_id: str,
        user_id: str,
        session_mode: str = "per_user",
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
            conversation_scope_id=conversation_scope_id,
            session_mode=session_mode,
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

    async def release_owned_conversations(self, platform: IMPlatform, science_user_id: str) -> int:
        return await self.conversation_binding_repo.release_by_owner(platform=platform, science_user_id=science_user_id)
