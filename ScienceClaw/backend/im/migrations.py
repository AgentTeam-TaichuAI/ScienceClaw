"""One-time data migrations for the IM subsystem."""
from __future__ import annotations

from loguru import logger
from backend.mongodb.db import db


async def backfill_session_sources() -> None:
    """Tag existing ScienceSession docs with `source` derived from im_chat_sessions."""
    im_col = db.get_collection("im_chat_sessions")
    sessions_col = db.get_collection("sessions")

    cursor = im_col.find(
        {"status": "active"},
        projection={"science_session_id": 1, "platform": 1},
    )

    updated = 0
    async for doc in cursor:
        sid = doc.get("science_session_id")
        platform = doc.get("platform")
        if not sid or not platform:
            continue

        update_fields: dict = {}
        session_doc = await sessions_col.find_one({"_id": sid}, projection={"source": 1, "pinned": 1})
        if not session_doc:
            continue
        if not session_doc.get("source"):
            update_fields["source"] = platform
        if platform == "wechat" and not session_doc.get("pinned"):
            update_fields["pinned"] = True
        if update_fields:
            await sessions_col.update_one({"_id": sid}, {"$set": update_fields})
            updated += 1

    if updated:
        logger.info(f"[Migration] Backfilled source/pinned for {updated} session(s)")
