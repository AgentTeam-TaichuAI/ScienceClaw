from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import shortuuid

from backend.im.base import IMPlatform
from backend.mongodb.db import db


@dataclass
class IMBindingToken:
    id: str
    platform: IMPlatform
    science_user_id: str
    token: str
    created_at: int
    updated_at: int
    expires_at: int
    status: str = "pending"
    platform_user_id: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.status == "pending" and self.expires_at > int(time.time())


class IMBindingTokenManager:
    def __init__(self):
        self.collection_name = "im_binding_tokens"

    async def get_active_token_by_science_user(
        self,
        platform: IMPlatform,
        science_user_id: str,
    ) -> Optional[IMBindingToken]:
        now = int(time.time())
        doc = await db.get_collection(self.collection_name).find_one(
            {
                "platform": platform.value,
                "science_user_id": science_user_id,
                "status": "pending",
                "expires_at": {"$gt": now},
            },
            sort=[("created_at", -1)],
        )
        if not doc:
            return None
        return self._doc_to_model(doc)

    async def create_or_refresh_token(
        self,
        platform: IMPlatform,
        science_user_id: str,
        ttl_seconds: int = 600,
    ) -> IMBindingToken:
        existing = await self.get_active_token_by_science_user(platform=platform, science_user_id=science_user_id)
        if existing:
            return existing

        now = int(time.time())
        expires_at = now + max(60, int(ttl_seconds))
        await db.get_collection(self.collection_name).update_many(
            {
                "platform": platform.value,
                "science_user_id": science_user_id,
                "status": "pending",
            },
            {
                "$set": {
                    "status": "replaced",
                    "updated_at": now,
                }
            },
        )

        binding_token = IMBindingToken(
            id=shortuuid.uuid(),
            platform=platform,
            science_user_id=science_user_id,
            token=shortuuid.uuid(),
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )
        await db.get_collection(self.collection_name).insert_one(
            {
                "_id": binding_token.id,
                "platform": binding_token.platform.value,
                "science_user_id": binding_token.science_user_id,
                "token": binding_token.token,
                "created_at": binding_token.created_at,
                "updated_at": binding_token.updated_at,
                "expires_at": binding_token.expires_at,
                "status": binding_token.status,
                "platform_user_id": binding_token.platform_user_id,
            }
        )
        return binding_token

    async def consume_token(
        self,
        platform: IMPlatform,
        token: str,
        platform_user_id: str,
    ) -> Optional[IMBindingToken]:
        now = int(time.time())
        collection = db.get_collection(self.collection_name)
        doc = await collection.find_one(
            {
                "platform": platform.value,
                "token": token,
                "status": "pending",
                "expires_at": {"$gt": now},
            }
        )
        if not doc:
            return None

        await collection.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": "consumed",
                    "platform_user_id": platform_user_id,
                    "updated_at": now,
                }
            },
        )
        updated = await collection.find_one({"_id": doc["_id"]})
        if not updated:
            return None
        return self._doc_to_model(updated)

    async def consume_single_pending_token(
        self,
        platform: IMPlatform,
        platform_user_id: str,
    ) -> Optional[IMBindingToken]:
        now = int(time.time())
        collection = db.get_collection(self.collection_name)
        docs: List[dict] = await collection.find(
            {
                "platform": platform.value,
                "status": "pending",
                "expires_at": {"$gt": now},
            }
        ).sort("created_at", -1).limit(2).to_list(length=2)
        if len(docs) != 1:
            return None

        doc = docs[0]
        result = await collection.update_one(
            {
                "_id": doc["_id"],
                "status": "pending",
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "status": "consumed",
                    "platform_user_id": platform_user_id,
                    "updated_at": now,
                }
            },
        )
        if int(result.modified_count or 0) != 1:
            return None
        updated = await collection.find_one({"_id": doc["_id"]})
        if not updated:
            return None
        return self._doc_to_model(updated)

    def _doc_to_model(self, doc: dict) -> IMBindingToken:
        return IMBindingToken(
            id=str(doc["_id"]),
            platform=IMPlatform(str(doc["platform"])),
            science_user_id=str(doc["science_user_id"]),
            token=str(doc["token"]),
            created_at=int(doc.get("created_at", 0)),
            updated_at=int(doc.get("updated_at", 0)),
            expires_at=int(doc.get("expires_at", 0)),
            status=str(doc.get("status") or "pending"),
            platform_user_id=(str(doc["platform_user_id"]) if doc.get("platform_user_id") is not None else None),
        )
