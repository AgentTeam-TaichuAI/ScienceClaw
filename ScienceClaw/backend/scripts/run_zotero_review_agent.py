r"""Run the Zotero Review Agent end-to-end and write results into an Obsidian vault.

Usage from the repo root:
  python .\ScienceClaw\backend\scripts\run_zotero_review_agent.py ^
    --input .\zotero\生成模型.json ^
    --topic 生成模型 ^
    --vault D:/Obsidian/MyVault ^
    --overwrite
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import types
from pathlib import Path


class _LocalToolWrapper:
    def __init__(self, fn):
        self._fn = fn

    def invoke(self, params):
        return self._fn(**params)

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


def _install_langchain_stub() -> None:
    try:
        import langchain_core.tools  # noqa: F401
        return
    except ImportError:
        pass

    tools_module = types.ModuleType("langchain_core.tools")

    def tool(fn):
        return _LocalToolWrapper(fn)

    tools_module.tool = tool

    root_module = types.ModuleType("langchain_core")
    root_module.tools = tools_module

    sys.modules["langchain_core"] = root_module
    sys.modules["langchain_core.tools"] = tools_module


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        tool_path = candidate / "Tools" / "obsidian_run_zotero_review_agent.py"
        if tool_path.exists():
            return candidate
    raise RuntimeError(f"Unable to locate repo root from {current}")


def _load_tool():
    _install_langchain_stub()

    repo_root = _find_repo_root()
    tool_path = repo_root / "Tools" / "obsidian_run_zotero_review_agent.py"
    spec = importlib.util.spec_from_file_location("obsidian_run_zotero_review_agent_module", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load tool from {tool_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_obj = getattr(module, "obsidian_run_zotero_review_agent", None)
    if tool_obj is None or not hasattr(tool_obj, "invoke"):
        raise RuntimeError("obsidian_run_zotero_review_agent tool is unavailable")
    return tool_obj


def _load_model_config(args: argparse.Namespace) -> str:
    inline_value = str(args.model_config_json or "").strip()
    file_value = str(args.model_config_file or "").strip()
    if inline_value and file_value:
        raise ValueError("Use only one of --model-config-json or --model-config-file")
    if file_value:
        config_path = Path(file_value).expanduser()
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        return config_path.read_text(encoding="utf-8")
    return inline_value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to Better BibTeX JSON export")
    parser.add_argument("--topic", default="", help="Review topic name; defaults to JSON filename stem")
    parser.add_argument("--category", default="", help="Category folder name; defaults to topic")
    parser.add_argument("--vault", default="", help="Existing Obsidian vault path to mount as OBSIDIAN_VAULT_DIR")
    parser.add_argument("--max-items", type=int, default=0, help="Max number of parent items to process; 0 = all")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing literature/review notes")
    parser.add_argument("--model-config-json", default="", help="Optional serialized model config JSON for the final polish pass")
    parser.add_argument("--model-config-file", default="", help="Optional UTF-8 JSON file containing the model config")
    args = parser.parse_args()

    if args.vault:
        os.environ["OBSIDIAN_VAULT_DIR"] = args.vault

    try:
        model_config_json = _load_model_config(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    tool_obj = _load_tool()
    result = tool_obj.invoke(
        {
            "export_json_path": args.input,
            "topic": args.topic,
            "category": args.category,
            "vault_dir": args.vault,
            "overwrite_existing": args.overwrite,
            "max_items": args.max_items,
            "model_config_json": model_config_json,
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
