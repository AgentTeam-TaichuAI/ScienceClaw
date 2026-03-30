r"""Import a Better BibTeX JSON export into the Materials subtree of an Obsidian vault.

Usage from the repo root:
  python .\ScienceClaw\backend\scripts\import_zotero_bbt_to_obsidian.py ^
    --input .\zotero\生成模型.json ^
    --topic 生成模型综述 ^
    --vault D:/Obsidian/MyVault
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


def _load_tool():
    _install_langchain_stub()

    repo_root = Path(__file__).resolve().parents[3]
    tool_path = repo_root / "Tools" / "obsidian_import_zotero_bbt_json.py"
    spec = importlib.util.spec_from_file_location("obsidian_import_zotero_bbt_json_module", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load tool from {tool_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_obj = getattr(module, "obsidian_import_zotero_bbt_json", None)
    if tool_obj is None or not hasattr(tool_obj, "invoke"):
        raise RuntimeError("obsidian_import_zotero_bbt_json tool is unavailable")
    return tool_obj


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to Better BibTeX JSON export")
    parser.add_argument("--topic", default="", help="Review topic name; defaults to JSON filename stem")
    parser.add_argument("--vault", default="", help="Existing Obsidian vault path to mount as OBSIDIAN_VAULT_DIR")
    parser.add_argument("--max-items", type=int, default=0, help="Max number of parent items to import; 0 = all")
    parser.add_argument("--alloy-family", default="", help="Optional alloy_family frontmatter value")
    parser.add_argument("--property-focus", default="", help="Optional property_focus frontmatter value")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing literature/review notes")
    parser.add_argument("--no-review", action="store_true", help="Skip creating the review note")
    args = parser.parse_args()

    if args.vault:
        os.environ["OBSIDIAN_VAULT_DIR"] = args.vault

    tool_obj = _load_tool()
    result = tool_obj.invoke(
        {
            "export_json_path": args.input,
            "topic": args.topic,
            "max_items": args.max_items,
            "alloy_family": args.alloy_family,
            "property_focus": args.property_focus,
            "vault_dir": args.vault,
            "overwrite_existing": args.overwrite,
            "create_review_note": not args.no_review,
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
