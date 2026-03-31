"""
Celery tasks: check_due_tasks (periodic) and run_task (execute one task).
Uses sync MongoDB (pymongo) and sync HTTP so worker does not need async.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import httpx
from croniter import croniter
from loguru import logger
from pymongo import MongoClient

from app.celery_app import app
from app.core.config import settings
from app.services.feishu import notify_task_failed, notify_task_success, notify_task_started


def _fmt_time(dt) -> str:
    """Format datetime to 'YYYY-MM-DD HH:MM:SS' in display timezone."""
    if dt is None:
        return "-"
    tz = _display_tz()
    if hasattr(dt, "astimezone"):
        dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _display_tz() -> ZoneInfo:
    """Return the configured display timezone (used for crontab matching)."""
    tz_name = (settings.display_timezone or "").strip() or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _get_sync_db():
    """Sync MongoDB connection for Celery worker."""
    auth = ""
    if settings.mongodb_username and settings.mongodb_password:
        auth = f"{settings.mongodb_username}:{settings.mongodb_password}@"
    uri = f"mongodb://{auth}{settings.mongodb_host}:{settings.mongodb_port}"
    client = MongoClient(uri)
    return client[settings.mongodb_db_name]


def _run_chat_sync(task_id: str, prompt: str, user_id: Optional[str] = None, model_config_id: Optional[str] = None) -> Dict[str, Any]:
    """Sync HTTP call to Chat Service. user_id: owner so the session appears in their Chats."""
    url = f"{settings.chat_service_url.rstrip('/')}/api/v1/chat"
    payload = {"input": prompt, "source": "task", "task_id": task_id}
    if user_id:
        payload["user_id"] = user_id
    if model_config_id:
        payload["model_config_id"] = model_config_id
    headers = {"Content-Type": "application/json"}
    if settings.chat_service_api_key:
        headers["X-API-Key"] = settings.chat_service_api_key
    try:
        with httpx.Client(timeout=300) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return {"error": f"Chat service {resp.status_code}: {resp.text[:500]}"}
            data = resp.json()
            if "error" in data:
                return data
            return {"chat_id": data.get("chat_id", ""), "output": data.get("output", "")}
    except Exception as e:
        logger.exception("Chat request failed")
        return {"error": str(e)}


def _notify_feishu_sync(
    webhook_url: str, task_name: str, start_time, end_time, success: bool, result_or_error: str
) -> None:
    if not webhook_url or not webhook_url.strip():
        return
    import asyncio
    start_str = _fmt_time(start_time)
    end_str = _fmt_time(end_time)
    if success:
        asyncio.run(notify_task_success(webhook_url, task_name, start_str, end_str, result_or_error))
    else:
        asyncio.run(notify_task_failed(webhook_url, task_name, start_str, end_str, result_or_error))


def _notify_start_sync(
    webhook_url: str, webhook_ids: list, db, task_name: str, start_time
) -> None:
    """Send task-started notification to all configured webhooks."""
    import asyncio
    from app.services.webhook_sender import send_webhook
    start_str = _fmt_time(start_time)
    if webhook_url and webhook_url.strip():
        asyncio.run(notify_task_started(webhook_url, task_name, start_str))
    if not webhook_ids:
        return
    title = f"🚀 任务开始执行：{task_name}"
    content = f"**⏱ 开始时间**\n{start_str}"
    for wid in webhook_ids:
        try:
            wh_doc = db.webhooks.find_one({"_id": wid})
            if not wh_doc:
                continue
            asyncio.run(
                send_webhook(
                    wh_doc.get("type", "feishu"),
                    wh_doc.get("url", ""),
                    title,
                    content,
                    wh_doc.get("config") or {},
                )
            )
        except Exception as e:
            logger.warning(f"Failed to notify start webhook {wid}: {e}")


def _notify_managed_webhooks_sync(
    db, webhook_ids: list, task_name: str, start_time, end_time, success: bool, result_or_error: str
) -> None:
    """Send notifications to all managed webhooks."""
    if not webhook_ids:
        return
    import asyncio
    from app.services.webhook_sender import send_webhook
    start_str = _fmt_time(start_time)
    end_str = _fmt_time(end_time)
    title = f"{'✅ 任务执行成功' if success else '❌ 任务执行失败'}：{task_name}"
    truncated = result_or_error[:500] + "..." if len(result_or_error) > 500 else result_or_error
    label = "执行结果" if success else "错误信息"
    content = f"**⏱ 开始时间**\n{start_str}\n\n**⏱ 结束时间**\n{end_str}\n\n**📋 {label}**\n\n{truncated}"
    for wid in webhook_ids:
        try:
            wh_doc = db.webhooks.find_one({"_id": wid})
            if not wh_doc:
                continue
            asyncio.run(
                send_webhook(
                    wh_doc.get("type", "feishu"),
                    wh_doc.get("url", ""),
                    title,
                    content,
                    wh_doc.get("config") or {},
                )
            )
        except Exception as e:
            logger.warning(f"Failed to notify webhook {wid}: {e}")


@app.task
def check_due_tasks() -> None:
    """Periodic: find tasks whose crontab matches current minute and dispatch run_task."""
    db = _get_sync_db()
    now = datetime.now(_display_tz())
    now = now.replace(second=0, microsecond=0)
    cursor = db.tasks.find({"status": "enabled"})
    for doc in cursor:
        crontab_str = doc.get("crontab") or ""
        if not crontab_str:
            continue
        try:
            if croniter.match(crontab_str, now):
                task_id = doc["_id"]
                app.send_task("app.tasks.run_task", args=[task_id])
                logger.info(f"Dispatched run_task for {task_id}")
        except Exception as e:
            logger.warning(f"Crontab check failed for task {doc.get('_id')}: {e}")


@app.task(bind=True)
def run_task(self, task_id: str) -> None:
    """
    Execute a single task: create task_run, call Chat API, update task_run, push Feishu.
    """
    db = _get_sync_db()
    doc = db.tasks.find_one({"_id": task_id})
    if not doc:
        logger.warning(f"run_task: task {task_id} not found")
        return
    name = doc.get("name", "未命名")
    prompt = doc.get("prompt", "")
    webhook = doc.get("webhook") or ""
    webhook_ids = doc.get("webhook_ids") or []
    event_config = doc.get("event_config") or []
    model_config_id = (doc.get("model_config_id") or "").strip() or None
    notify_start = "notify_on_start" in event_config
    user_id = (doc.get("user_id") or "").strip() or None
    start_time = datetime.now(timezone.utc)
    inserted_id = None
    try:
        run_doc: Dict[str, Any] = {
            "task_id": task_id,
            "status": "pending",
            "chat_id": None,
            "start_time": start_time,
            "end_time": None,
            "result": None,
            "error": None,
        }
        ins = db.task_runs.insert_one(run_doc)
        inserted_id = ins.inserted_id

        db.task_runs.update_one({"_id": inserted_id}, {"$set": {"status": "running"}})

        if notify_start:
            _notify_start_sync(webhook, webhook_ids, db, name, start_time)

        result = _run_chat_sync(task_id, prompt, user_id=user_id, model_config_id=model_config_id)
        end_time = datetime.now(timezone.utc)
        if "error" in result:
            db.task_runs.update_one(
                {"_id": inserted_id},
                {"$set": {"status": "failed", "end_time": end_time, "error": result["error"]}},
            )
            _notify_feishu_sync(webhook, name, start_time, end_time, False, result["error"])
            _notify_managed_webhooks_sync(db, webhook_ids, name, start_time, end_time, False, result["error"])
            return
        db.task_runs.update_one(
            {"_id": inserted_id},
            {
                "$set": {
                    "status": "success",
                    "chat_id": result.get("chat_id"),
                    "end_time": end_time,
                    "result": result.get("output", ""),
                    "error": None,
                }
            },
        )
        _notify_feishu_sync(webhook, name, start_time, end_time, True, result.get("output", ""))
        _notify_managed_webhooks_sync(db, webhook_ids, name, start_time, end_time, True, result.get("output", ""))
    except Exception as e:
        logger.exception(f"run_task failed for {task_id}")
        end_time = datetime.now(timezone.utc)
        if inserted_id is not None:
            db.task_runs.update_one(
                {"_id": inserted_id},
                {"$set": {"status": "failed", "end_time": end_time, "error": str(e)}},
            )
        _notify_feishu_sync(webhook, name, start_time, end_time, False, str(e))
        _notify_managed_webhooks_sync(db, webhook_ids, name, start_time, end_time, False, str(e))
