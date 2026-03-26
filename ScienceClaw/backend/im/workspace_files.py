from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.im.base import IMAttachment

ROUND_FILES_EXCLUDE_DIRS = {"_diagnostic", "tools_staging", "__pycache__", ".git", "incoming"}
ROUND_FILES_EXCLUDE_NAMES = {"CONTEXT.md", "planner.md", "AGENTS.md"}
STICKER_EXTENSIONS = {".tgs", ".webm"}
VOICE_EXTENSIONS = {".ogg", ".oga", ".opus"}


def snapshot_workspace_files(workspace_dir: Path) -> Dict[str, float]:
    snap: Dict[str, float] = {}
    if not workspace_dir.is_dir():
        return snap
    for fp in workspace_dir.rglob("*"):
        if not fp.is_file():
            continue
        try:
            rel = str(fp.relative_to(workspace_dir)).replace("\\", "/")
            snap[rel] = fp.stat().st_mtime
        except (OSError, ValueError):
            continue
    return snap


def diff_workspace_files(
    pre: Dict[str, float],
    post: Dict[str, float],
    workspace_dir: Path,
    session_id: str,
) -> List[Dict[str, Any]]:
    changed: List[Dict[str, Any]] = []
    for rel, mtime in post.items():
        top_dir = rel.split("/", 1)[0] if "/" in rel else ""
        if top_dir in ROUND_FILES_EXCLUDE_DIRS:
            continue
        basename = rel.rsplit("/", 1)[-1]
        if basename in ROUND_FILES_EXCLUDE_NAMES or basename.startswith("."):
            continue

        prev_mtime = pre.get(rel)
        if prev_mtime is not None and prev_mtime >= mtime:
            continue

        fp = workspace_dir / rel
        try:
            stat = fp.stat()
        except OSError:
            continue

        upload_date = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        category = "research_data" if top_dir == "research_data" else "output"
        changed.append(
            {
                "file_id": str(fp),
                "filename": basename,
                "relative_path": rel,
                "size": stat.st_size,
                "upload_date": upload_date,
                "file_url": f"/api/v1/sessions/{session_id}/sandbox-file/download?path={fp}",
                "category": category,
            }
        )
    return changed


def guess_attachment_kind(file_path: str, mime_type: Optional[str] = None, filename: Optional[str] = None) -> str:
    path = Path(file_path)
    name = (filename or path.name or "").lower()
    suffix = path.suffix.lower()
    guessed_mime = mime_type or mimetypes.guess_type(name)[0] or ""

    if suffix in STICKER_EXTENSIONS or (suffix == ".webp" and "sticker" in name):
        return "sticker"
    if guessed_mime == "image/gif":
        return "animation"
    if guessed_mime.startswith("image/"):
        return "photo"
    if suffix in VOICE_EXTENSIONS:
        return "voice"
    if guessed_mime.startswith("audio/"):
        return "audio"
    if guessed_mime.startswith("video/"):
        return "video"
    return "document"


def build_output_attachments(changed_files: List[Dict[str, Any]]) -> List[IMAttachment]:
    attachments: List[IMAttachment] = []
    for item in changed_files:
        file_path = str(item.get("file_id") or "")
        filename = str(item.get("filename") or Path(file_path).name)
        mime_type = mimetypes.guess_type(filename)[0]
        attachments.append(
            IMAttachment(
                kind=guess_attachment_kind(file_path=file_path, mime_type=mime_type, filename=filename),
                file_path=file_path,
                filename=filename,
                mime_type=mime_type,
                metadata={
                    "relative_path": item.get("relative_path"),
                    "category": item.get("category"),
                    "size": item.get("size"),
                },
            )
        )
    return attachments
