from typing import Optional
from pydantic import BaseModel, Field

from backend.mongodb.db import db

# Defaults tuned for 128K context window models (e.g. DeepSeek v3.2):
#   max_tokens      = 8K    — output ceiling, sufficient for most single-step replies
#   output_reserve  = 16K   — reserved in history budget calc (actual per-step output)
#   history_budget  = 128000 × 0.85 - (16384 + 4000 + 6000 + 1000) ≈ 81K tokens
#   max_history_rounds = 10 — safe under 81K budget
DEFAULT_AGENT_STREAM_TIMEOUT = 10800
DEFAULT_SANDBOX_EXEC_TIMEOUT = 1200
DEFAULT_MAX_TOKENS = 8192
DEFAULT_OUTPUT_RESERVE = 16384
DEFAULT_MAX_HISTORY_ROUNDS = 10
DEFAULT_MAX_OUTPUT_CHARS = 50000


class TaskSettings(BaseModel):
    agent_stream_timeout: int = Field(
        default=DEFAULT_AGENT_STREAM_TIMEOUT,
        ge=60, le=21600,
        description="Agent task max execution time in seconds",
    )
    sandbox_exec_timeout: int = Field(
        default=DEFAULT_SANDBOX_EXEC_TIMEOUT,
        ge=30, le=1800,
        description="Single sandbox command timeout in seconds",
    )
    max_tokens: int = Field(
        default=DEFAULT_MAX_TOKENS,
        ge=1024, le=200000,
        description="LLM max output tokens (ceiling for model reply length)",
    )
    output_reserve: int = Field(
        default=DEFAULT_OUTPUT_RESERVE,
        ge=2048, le=65536,
        description="Tokens reserved for output in history budget calculation",
    )
    max_history_rounds: int = Field(
        default=DEFAULT_MAX_HISTORY_ROUNDS,
        ge=1, le=30,
        description="Number of history conversation rounds in context",
    )
    max_output_chars: int = Field(
        default=DEFAULT_MAX_OUTPUT_CHARS,
        ge=5000, le=100000,
        description="Max chars of sandbox output before truncation",
    )
    obsidian_vault_dir: str = Field(
        default="",
        max_length=1024,
        description="Preferred Obsidian vault path for materials-note tools",
    )


class UpdateTaskSettingsRequest(BaseModel):
    agent_stream_timeout: Optional[int] = Field(default=None, ge=60, le=21600)
    sandbox_exec_timeout: Optional[int] = Field(default=None, ge=30, le=1800)
    max_tokens: Optional[int] = Field(default=None, ge=1024, le=200000)
    output_reserve: Optional[int] = Field(default=None, ge=2048, le=65536)
    max_history_rounds: Optional[int] = Field(default=None, ge=1, le=30)
    max_output_chars: Optional[int] = Field(default=None, ge=5000, le=100000)
    obsidian_vault_dir: Optional[str] = Field(default=None, max_length=1024)


async def get_task_settings(user_id: str) -> TaskSettings:
    doc = await db.get_collection("task_settings").find_one({"_id": user_id})
    if not doc:
        return TaskSettings()
    doc.pop("_id", None)
    return TaskSettings(**doc)


async def update_task_settings(user_id: str, updates: UpdateTaskSettingsRequest) -> TaskSettings:
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return await get_task_settings(user_id)

    await db.get_collection("task_settings").update_one(
        {"_id": user_id},
        {"$set": update_data},
        upsert=True,
    )
    return await get_task_settings(user_id)
