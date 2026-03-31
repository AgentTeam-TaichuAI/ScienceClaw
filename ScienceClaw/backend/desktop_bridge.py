from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

_DEFAULT_BRIDGE_CANDIDATES = [
    "http://127.0.0.1:8765",
    "http://host.docker.internal:8765",
]


def _bridge_candidates() -> list[str]:
    configured = (os.environ.get("OBSIDIAN_HOST_BRIDGE_URL", "") or "").strip()
    candidates: list[str] = []
    if configured:
        candidates.append(configured.rstrip("/"))
    for candidate in _DEFAULT_BRIDGE_CANDIDATES:
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _bridge_headers() -> dict[str, str]:
    return {
        "X-Bridge-Token": os.environ.get("OBSIDIAN_HOST_BRIDGE_TOKEN", "scienceclaw-local-bridge"),
    }


async def request_desktop_bridge(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    last_error: Exception | None = None
    normalized_path = path if path.startswith("/") else f"/{path}"

    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        for base_url in _bridge_candidates():
            try:
                response = await client.request(
                    method.upper(),
                    f"{base_url}{normalized_path}",
                    json=payload,
                    headers=_bridge_headers(),
                )
                data = response.json() if response.content else {}
                return {
                    "ok": response.is_success,
                    "status_code": response.status_code,
                    "base_url": base_url,
                    "data": data,
                }
            except Exception as exc:
                last_error = exc

    return {
        "ok": False,
        "status_code": 503,
        "base_url": "",
        "data": {
            "ok": False,
            "error": f"Desktop bridge unavailable: {last_error}" if last_error else "Desktop bridge unavailable",
        },
    }


def request_desktop_bridge_sync(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    return asyncio.run(request_desktop_bridge(method, path, payload=payload, timeout=timeout))


async def request_host_read_file(path: str, timeout: float = 60.0) -> dict[str, Any]:
    return await request_desktop_bridge(
        "POST",
        "/host/read-file",
        {"path": path},
        timeout=timeout,
    )


def request_host_read_file_sync(path: str, timeout: float = 60.0) -> dict[str, Any]:
    return request_desktop_bridge_sync(
        "POST",
        "/host/read-file",
        {"path": path},
        timeout=timeout,
    )
