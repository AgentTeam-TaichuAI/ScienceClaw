from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from backend.im.adapters.telegram import TelegramAdapter
from backend.im.base import IMPlatform
from backend.im.orchestrator import IMServiceOrchestrator


class TelegramPollingService:
    def __init__(
        self,
        orchestrator: IMServiceOrchestrator,
        adapter: TelegramAdapter,
        timeout_seconds: int = 30,
    ):
        self.orchestrator = orchestrator
        self.adapter = adapter
        self.timeout_seconds = max(5, min(int(timeout_seconds), 60))
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._offset: Optional[int] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="telegram-polling")
        logger.info("telegram polling service started")

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("telegram polling service stopped")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                updates = await self.adapter.get_updates(offset=self._offset, timeout=self.timeout_seconds)
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        self._offset = update_id + 1
                    message = self.adapter.parse_update(update)
                    if not message:
                        continue
                    await self.orchestrator.handle_incoming_message(IMPlatform.TELEGRAM, message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"telegram polling loop failed: {exc}")
                await asyncio.sleep(2)
