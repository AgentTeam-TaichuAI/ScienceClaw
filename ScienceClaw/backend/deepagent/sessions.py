import asyncio
import os
import shortuuid
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

from loguru import logger
from backend.mongodb.db import db
from backend.deepagent.plan_types import PlanStep

_BASE_WORKSPACE = os.environ.get("WORKSPACE_DIR", "/home/scienceclaw")


def _render_planner_md(plan: List[PlanStep]) -> str:
    lines: list[str] = ["# Planner", ""]
    if not plan:
        lines.append("_No plan yet._")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Steps")
    lines.append("")
    for step in plan:
        status = (step.get("status") or "pending").strip()
        checked = "x" if status == "completed" else " "
        tools = ", ".join(step.get("tools") or [])
        suffix = f" (tools: {tools})" if tools else ""
        lines.append(f"- [{checked}] {step['id']} [{status}] {step['content']}{suffix}")
    lines.append("")
    return "\n".join(lines)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


@dataclass
class ScienceSession:
    session_id: str
    thread_id: str
    vm_root_dir: Path
    mode: str = "deep"
    plan: List[PlanStep] = field(default_factory=list)
    user_id: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None

    _planner_md_digest: str = field(default="", repr=False)
    events: List[Dict[str, Any]] = field(default_factory=list)
    _is_cancelled: bool = field(default=False, init=False, repr=False)

    title: Optional[str] = None
    status: str = "pending"
    created_at: int = 0
    updated_at: int = 0
    unread_message_count: int = 0
    is_shared: bool = False
    latest_message: str = ""
    latest_message_at: int = 0
    pinned: bool = False
    source: Optional[str] = None

    _shell_sessions: Dict[str, Any] = field(default_factory=dict)

    def cancel(self) -> None:
        self._is_cancelled = True
        logger.info(f"Session {self.session_id} marked as cancelled")

    def reset_cancel(self) -> None:
        self._is_cancelled = False

    def is_cancelled(self) -> bool:
        return getattr(self, "_is_cancelled", False)

    def get_plan(self) -> List[PlanStep]:
        return list(self.plan)

    def set_plan(self, plan: List[PlanStep]) -> None:
        self.plan = list(plan)
        self._sync_planner_md()
        self._persist_update({"plan": self.plan})

    def _sync_planner_md(self) -> None:
        try:
            content = _render_planner_md(self.plan)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if digest == self._planner_md_digest:
                return
            _atomic_write_text(self.vm_root_dir / "planner.md", content)
            self._planner_md_digest = digest
        except Exception:
            logger.exception("sync planner.md failed for session {}", self.session_id)

    def ls(self, path: str) -> List[Dict[str, object]]:
        """List files under the session workspace directory."""
        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        full_path = self.vm_root_dir / path.lstrip("/")
        items: List[Dict[str, object]] = []
        if full_path.is_dir():
            for entry in sorted(full_path.iterdir()):
                items.append({
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                })
        return items

    def _persist_update(self, update_dict: Dict[str, Any]) -> None:
        pass

    async def save(self):
        update_data = {
            "mode": self.mode,
            "plan": self.plan,
            "title": self.title,
            "status": self.status,
            "updated_at": int(time.time()),
            "unread_message_count": self.unread_message_count,
            "is_shared": self.is_shared,
            "latest_message": self.latest_message,
            "latest_message_at": self.latest_message_at,
            "model_config": self.model_config,
            "events": self.events,
            "pinned": self.pinned,
            "source": self.source,
        }
        await db.get_collection("sessions").update_one(
            {"_id": self.session_id},
            {"$set": update_data},
            upsert=True
        )


class ScienceSessionNotFoundError(KeyError):
    pass


_sessions_lock = asyncio.Lock()
_SESSION_CACHE_MAX = 200
_SESSION_CACHE_TTL = 3600
_sessions: Dict[str, ScienceSession] = {}
_sessions_atime: Dict[str, float] = {}


def _evict_stale_sessions() -> None:
    """Remove expired entries when cache exceeds max size (called under lock)."""
    if len(_sessions) <= _SESSION_CACHE_MAX:
        return
    now = time.time()
    expired = [
        sid for sid, ts in _sessions_atime.items()
        if now - ts > _SESSION_CACHE_TTL
    ]
    for sid in expired:
        _sessions.pop(sid, None)
        _sessions_atime.pop(sid, None)
    if len(_sessions) > _SESSION_CACHE_MAX:
        oldest = sorted(_sessions_atime, key=_sessions_atime.get)
        for sid in oldest[: len(_sessions) - _SESSION_CACHE_MAX]:
            _sessions.pop(sid, None)
            _sessions_atime.pop(sid, None)


def _session_workspace(session_id: str) -> Path:
    """Return the workspace directory for a session: /home/scienceclaw/{session_id}"""
    return Path(_BASE_WORKSPACE) / session_id


async def async_create_science_session(
    mode: str = "deep",
    user_id: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> ScienceSession:
    session_id = shortuuid.uuid()
    thread_id = session_id

    vm_root = _session_workspace(session_id)
    vm_root.mkdir(parents=True, exist_ok=True)
    vm_root.chmod(0o777)

    now = int(time.time())
    session = ScienceSession(
        session_id=session_id,
        thread_id=thread_id,
        vm_root_dir=vm_root,
        mode=mode,
        user_id=user_id,
        model_config=model_config,
        created_at=now,
        updated_at=now,
        source=source,
    )

    session_doc = {
        "_id": session_id,
        "thread_id": thread_id,
        "user_id": user_id,
        "mode": mode,
        "model_config": model_config,
        "vm_root_dir": str(vm_root),
        "created_at": now,
        "updated_at": now,
        "status": "pending",
        "events": [],
        "plan": [],
    }
    if source:
        session_doc["source"] = source
    await db.get_collection("sessions").insert_one(session_doc)

    async with _sessions_lock:
        _sessions[session_id] = session
        _sessions_atime[session_id] = time.time()
        _evict_stale_sessions()

    logger.info(f"Created session {session_id} (workspace={vm_root}, user={user_id})")
    return session


async def async_get_science_session(session_id: str) -> ScienceSession:
    async with _sessions_lock:
        session = _sessions.get(session_id)
        if session:
            _sessions_atime[session_id] = time.time()

    if session:
        return session

    doc = await db.get_collection("sessions").find_one({"_id": session_id})
    if not doc:
        raise ScienceSessionNotFoundError(f"session {session_id} not found")

    vm_root = Path(doc.get("vm_root_dir") or str(_session_workspace(session_id)))
    vm_root.mkdir(parents=True, exist_ok=True)
    vm_root.chmod(0o777)

    session = ScienceSession(
        session_id=session_id,
        thread_id=doc["thread_id"],
        vm_root_dir=vm_root,
        mode=doc.get("mode", "deep"),
        user_id=doc.get("user_id"),
        model_config=doc.get("model_config"),
        plan=doc.get("plan", []),
        events=doc.get("events", []),
        title=doc.get("title"),
        status=doc.get("status", "pending"),
        created_at=doc.get("created_at", 0),
        updated_at=doc.get("updated_at", 0),
        unread_message_count=doc.get("unread_message_count", 0),
        is_shared=doc.get("is_shared", False),
        latest_message=doc.get("latest_message", ""),
        latest_message_at=doc.get("latest_message_at", 0),
        pinned=doc.get("pinned", False),
        source=doc.get("source"),
    )

    async with _sessions_lock:
        _sessions[session_id] = session
        _sessions_atime[session_id] = time.time()

    return session


async def async_list_science_sessions(user_id: Optional[str] = None) -> List[ScienceSession]:
    query: Dict[str, Any] = {"source": {"$ne": "task"}}
    if user_id:
        query["user_id"] = user_id

    cursor = db.get_collection("sessions").find(query).sort("updated_at", -1)
    sessions = []

    async with _sessions_lock:
        cached_snapshot = dict(_sessions)

    async for doc in cursor:
        cached = cached_snapshot.get(doc["_id"])

        if cached:
            sessions.append(cached)
            continue

        vm_root = Path(doc.get("vm_root_dir") or str(_session_workspace(doc["_id"])))

        s = ScienceSession(
            session_id=doc["_id"],
            thread_id=doc["thread_id"],
            vm_root_dir=vm_root,
            mode=doc.get("mode", "deep"),
            user_id=doc.get("user_id"),
            model_config=doc.get("model_config"),
            title=doc.get("title"),
            status=doc.get("status", "pending"),
            created_at=doc.get("created_at", 0),
            updated_at=doc.get("updated_at", 0),
            unread_message_count=doc.get("unread_message_count", 0),
            is_shared=doc.get("is_shared", False),
            latest_message=doc.get("latest_message", ""),
            latest_message_at=doc.get("latest_message_at", 0),
            pinned=doc.get("pinned", False),
            source=doc.get("source"),
        )
        sessions.append(s)

    return sessions


async def async_delete_science_session(session_id: str) -> None:
    res = await db.get_collection("sessions").delete_one({"_id": session_id})
    if res.deleted_count == 0:
        raise ScienceSessionNotFoundError(f"session {session_id} not found")

    async with _sessions_lock:
        _sessions.pop(session_id, None)
        _sessions_atime.pop(session_id, None)

    workspace = Path(_BASE_WORKSPACE) / session_id
    if workspace.is_dir():
        import shutil
        try:
            shutil.rmtree(workspace)
            logger.info(f"[Session] Deleted workspace: {workspace}")
        except Exception as exc:
            logger.warning(f"[Session] Failed to delete workspace {workspace}: {exc}")


def create_science_session(*args, **kwargs):
    raise RuntimeError("Use async_create_science_session")

def get_science_session(session_id: str):
    raise RuntimeError("Use async_get_science_session")

def list_science_sessions():
    raise RuntimeError("Use async_list_science_sessions")

def delete_science_session(session_id: str):
    raise RuntimeError("Use async_delete_science_session")
