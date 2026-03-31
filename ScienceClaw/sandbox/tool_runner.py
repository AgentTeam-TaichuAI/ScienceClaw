#!/usr/bin/env python3
"""
tool_runner.py — 沙箱环境中的 @tool 函数执行器。

被 Backend 代理工具通过 sandbox shell/exec 调用，
在沙箱 Python 环境中加载并执行 @tool 函数，确保测试环境 = 生产环境。

用法:
    python3 /app/_tool_runner.py <tool_file> <func_name> '<json_args>'
    python3 /app/_tool_runner.py <tool_file> <func_name> --args-file /tmp/args.json

输出:
    以标记包裹的 JSON 结果（便于可靠解析，避免与工具自身的 print 混淆）:
    >>>TOOL_RESULT_JSON>>>
    {"key": "value", ...}
    <<<TOOL_RESULT_JSON<<<
"""
import sys
import json
import importlib.util
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

_START_MARKER = ">>>TOOL_RESULT_JSON>>>"
_END_MARKER = "<<<TOOL_RESULT_JSON<<<"


def _emit(payload: dict) -> None:
    print(_START_MARKER)
    print(json.dumps(payload, ensure_ascii=False, default=str))
    print(_END_MARKER)


def main() -> None:
    if len(sys.argv) < 3:
        _emit({"error": f"Usage: {sys.argv[0]} <tool_file> <func_name> [json_args]"})
        sys.exit(1)

    tool_file = sys.argv[1]
    func_name = sys.argv[2]
    args_json = "{}"
    args_file: Path | None = None
    if len(sys.argv) > 4 and sys.argv[3] == "--args-file":
        args_file = Path(sys.argv[4])
        args_json = args_file.read_text(encoding="utf-8")
    else:
        args_json = sys.argv[3] if len(sys.argv) > 3 else "{}"

    try:
        try:
            args = json.loads(args_json)
        except json.JSONDecodeError as e:
            _emit({"error": f"Invalid JSON args: {e}"})
            sys.exit(1)

        try:
            spec = importlib.util.spec_from_file_location("_tool_mod", tool_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create module spec from {tool_file}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            _emit({"error": f"Failed to load tool module '{tool_file}': {e}"})
            sys.exit(1)

        tool_obj = getattr(mod, func_name, None)
        if tool_obj is None:
            _emit({"error": f"Function '{func_name}' not found in {tool_file}"})
            sys.exit(1)

        try:
            result = tool_obj.invoke(args)
        except Exception as e:
            _emit({"error": f"Tool execution failed: {type(e).__name__}: {e}"})
            sys.exit(1)

        _emit(result)
    finally:
        if args_file is not None:
            try:
                args_file.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
