from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any


HOST = os.environ.get("SC_OBSIDIAN_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("SC_OBSIDIAN_BRIDGE_PORT", "8765"))
TOKEN = os.environ.get("SC_OBSIDIAN_BRIDGE_TOKEN") or os.environ.get("OBSIDIAN_HOST_BRIDGE_TOKEN", "scienceclaw-local-bridge")
MATERIALS_ROOT = PurePosixPath("Research/Materials")
_HOST_READ_SUFFIXES = {".pdf", ".html", ".htm", ".txt", ".md", ".json"}


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8")) if raw else {}


def _require_token(handler: BaseHTTPRequestHandler) -> bool:
    provided = handler.headers.get("X-Bridge-Token", "")
    if provided == TOKEN:
        return True
    _json_response(handler, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Invalid bridge token"})
    return False


def _normalize_vault_dir(raw: str, create_if_missing: bool = False) -> Path:
    vault_dir = Path(str(raw or "").strip()).expanduser()
    if not vault_dir.is_absolute():
        raise ValueError("vault_dir must be an absolute path")
    if vault_dir.exists():
        if not vault_dir.is_dir():
            raise ValueError("vault_dir exists but is not a directory")
    elif create_if_missing:
        vault_dir.mkdir(parents=True, exist_ok=True)
    else:
        raise FileNotFoundError(f"vault_dir does not exist: {vault_dir}")
    return vault_dir


def _host_read_roots() -> list[Path]:
    configured = str(os.environ.get("SC_HOST_READ_ROOTS", "") or "").strip()
    if not configured:
        return []

    roots: list[Path] = []
    for entry in configured.split(os.pathsep):
        raw = entry.strip().strip('"')
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        if candidate.exists() and candidate.is_dir():
            roots.append(candidate.resolve())
    return roots


def _normalize_host_read_path(raw: str) -> Path:
    file_path = Path(str(raw or "").strip()).expanduser()
    if not file_path.is_absolute():
        raise ValueError("path must be an absolute path")
    if not file_path.exists():
        raise FileNotFoundError(f"path does not exist: {file_path}")
    if not file_path.is_file():
        raise ValueError("path exists but is not a file")

    resolved = file_path.resolve()
    if resolved.suffix.lower() not in _HOST_READ_SUFFIXES:
        raise ValueError(
            f"file suffix {resolved.suffix or '<none>'} is not allowed; "
            f"allowed suffixes: {', '.join(sorted(_HOST_READ_SUFFIXES))}"
        )

    roots = _host_read_roots()
    if not roots:
        raise ValueError("SC_HOST_READ_ROOTS is not configured on the host bridge")

    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(f"path is outside allowed host read roots: {resolved}")


def _materials_subdirs() -> list[PurePosixPath]:
    return [
        MATERIALS_ROOT,
        MATERIALS_ROOT / "Literature Notes",
        MATERIALS_ROOT / "Review Notes",
        MATERIALS_ROOT / "Templates",
    ]


def _safe_folder_component(raw: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n]+', " ", str(raw or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120].strip()


def _materials_subdirs_for_category(category: str) -> list[PurePosixPath]:
    base_dirs = _materials_subdirs()
    category_dir = _safe_folder_component(category)
    if not category_dir:
        return base_dirs
    return base_dirs + [
        MATERIALS_ROOT / "Literature Notes" / category_dir,
        MATERIALS_ROOT / "Review Notes" / category_dir,
    ]


def _legacy_materials_dirs() -> list[PurePosixPath]:
    return [
        MATERIALS_ROOT / "Datasets",
        MATERIALS_ROOT / "Figures",
        MATERIALS_ROOT / "Projects",
    ]


def _safe_materials_relative_path(relative_path: str) -> PurePosixPath:
    rel = PurePosixPath(str(relative_path or "").replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) == 0:
        raise ValueError("relative_path must be a safe relative path")
    if rel.parts[:2] != MATERIALS_ROOT.parts:
        raise ValueError("relative_path must stay inside Research/Materials")
    return rel


def _to_os_path(vault_dir: Path, relative_path: PurePosixPath) -> Path:
    current = vault_dir
    for part in relative_path.parts:
        current = current / part
    return current


def _pick_directory_tk(title: str, initial_dir: str) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            title=title or "Select Obsidian vault",
            initialdir=initial_dir or None,
            mustexist=False,
        )
        return selected or ""
    finally:
        root.destroy()


def _pick_directory_powershell(title: str, initial_dir: str) -> str:
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = @"
{title or "Select Obsidian vault"}
"@
if ('{initial_dir}'.Length -gt 0) {{ $dialog.SelectedPath = '{initial_dir}' }}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  Write-Output $dialog.SelectedPath
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "").strip()


def _pick_directory(title: str, initial_dir: str) -> str:
    try:
        return _pick_directory_tk(title, initial_dir)
    except Exception:
        return _pick_directory_powershell(title, initial_dir)


class ObsidianHostBridgeHandler(BaseHTTPRequestHandler):
    server_version = "ScienceClawObsidianBridge/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "ok": True,
                    "status": "ok",
                    "host": HOST,
                    "port": PORT,
                },
            )
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Route not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not _require_token(self):
            return

        try:
            body = _read_json(self)
        except Exception as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        try:
            if self.path == "/pick-directory":
                self._handle_pick_directory(body)
            elif self.path == "/host/read-file":
                self._handle_host_read_file(body)
            elif self.path == "/obsidian/ensure-vault":
                self._handle_ensure_vault(body)
            elif self.path == "/obsidian/bootstrap-materials":
                self._handle_bootstrap_materials(body)
            elif self.path == "/obsidian/prune-materials-legacy":
                self._handle_prune_materials_legacy(body)
            elif self.path == "/obsidian/write-file":
                self._handle_write_file(body)
            else:
                _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Route not found"})
        except FileExistsError as exc:
            _json_response(self, HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
        except FileNotFoundError as exc:
            _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:  # pragma: no cover - guardrail
            _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def _handle_pick_directory(self, body: dict[str, Any]) -> None:
        title = str(body.get("title", "Select Obsidian vault"))
        initial_dir = str(body.get("initial_dir", "")).strip()
        selected = _pick_directory(title, initial_dir)
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "cancelled": not bool(selected),
                "path": selected,
            },
        )

    def _handle_host_read_file(self, body: dict[str, Any]) -> None:
        file_path = _normalize_host_read_path(str(body.get("path", "")))
        raw = file_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "path": str(file_path),
                "name": file_path.name,
                "suffix": file_path.suffix.lower(),
                "size": len(raw),
                "mime_type": mime_type or "application/octet-stream",
                "content_base64": base64.b64encode(raw).decode("ascii"),
            },
        )

    def _handle_ensure_vault(self, body: dict[str, Any]) -> None:
        vault_dir = _normalize_vault_dir(str(body.get("vault_dir", "")), create_if_missing=bool(body.get("create_if_missing", False)))
        category = _safe_folder_component(str(body.get("category", "")))
        created_dirs: list[str] = []
        if body.get("bootstrap_materials"):
            for rel in _materials_subdirs_for_category(category):
                target = _to_os_path(vault_dir, rel)
                if not target.exists():
                    target.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(rel.as_posix())
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "vault_dir": str(vault_dir),
                "has_obsidian_config": (vault_dir / ".obsidian").exists(),
                "materials_root": str(_to_os_path(vault_dir, MATERIALS_ROOT)),
                "category": category,
                "created_dirs": created_dirs,
            },
        )

    def _handle_bootstrap_materials(self, body: dict[str, Any]) -> None:
        vault_dir = _normalize_vault_dir(str(body.get("vault_dir", "")), create_if_missing=bool(body.get("create_if_missing", False)))
        templates = body.get("templates", {}) or {}
        overwrite_templates = bool(body.get("overwrite_templates", False))
        category = _safe_folder_component(str(body.get("category", "")))

        created_dirs: list[str] = []
        for rel in _materials_subdirs_for_category(category):
            target = _to_os_path(vault_dir, rel)
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
                created_dirs.append(rel.as_posix())

        created_templates: list[str] = []
        for name, content in templates.items():
            rel = MATERIALS_ROOT / "Templates" / str(name)
            target = _to_os_path(vault_dir, rel)
            if overwrite_templates or not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(content), encoding="utf-8")
                created_templates.append(rel.as_posix())

        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "vault_dir": str(vault_dir),
                "materials_root": str(_to_os_path(vault_dir, MATERIALS_ROOT)),
                "category": category,
                "created_dirs": created_dirs,
                "created_templates": created_templates,
            },
        )

    def _handle_prune_materials_legacy(self, body: dict[str, Any]) -> None:
        vault_dir = _normalize_vault_dir(str(body.get("vault_dir", "")), create_if_missing=False)
        removed_dirs: list[str] = []
        skipped_nonempty: list[str] = []
        for rel in _legacy_materials_dirs():
            target = _to_os_path(vault_dir, rel)
            if not target.exists():
                continue
            if any(target.iterdir()):
                skipped_nonempty.append(rel.as_posix())
                continue
            target.rmdir()
            removed_dirs.append(rel.as_posix())

        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "vault_dir": str(vault_dir),
                "removed_dirs": removed_dirs,
                "skipped_nonempty": skipped_nonempty,
            },
        )

    def _handle_write_file(self, body: dict[str, Any]) -> None:
        vault_dir = _normalize_vault_dir(str(body.get("vault_dir", "")), create_if_missing=False)
        relative_path = _safe_materials_relative_path(str(body.get("relative_path", "")))
        content = str(body.get("content", ""))
        overwrite = bool(body.get("overwrite", False))

        target = _to_os_path(vault_dir, relative_path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {relative_path.as_posix()}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "vault_dir": str(vault_dir),
                "relative_path": relative_path.as_posix(),
                "absolute_path": str(target),
            },
        )


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ObsidianHostBridgeHandler)
    print(f"ScienceClaw Obsidian host bridge listening on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
