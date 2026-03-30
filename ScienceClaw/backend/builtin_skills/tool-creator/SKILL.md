---
name: tool-creator
description: "Create new tools or upgrade existing tools for the agent. MANDATORY: Use this skill whenever the user wants to create a custom tool, convert a script into a reusable tool, write a new tool function, upgrade or modify an existing tool, test and improve a tool in the sandbox, or asks things like 'make a tool for X', 'create a tool that does Y', 'improve the X tool', 'upgrade my tool', 'turn this script into a tool'. Even if the user doesn't use the word 'tool' explicitly, trigger this if they want to add a new callable capability to the agent or modify an existing one."
---

# Tool Creator

A skill for creating new agent tools and upgrading existing ones.

Tools are Python functions decorated with `@tool` from `langchain_core.tools` that the agent can call directly during conversations. Unlike skills (which are instruction documents), tools are executable code that extend the agent's capabilities.

## Tool Format

Every tool MUST follow this exact pattern to be compatible with the deepagents framework:

```python
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Models & Prediction",
    "subcategory": "Materials Science",
    "tags": ["materials", "dft", "phase-diagram"],
}


@tool
def my_tool_name(param1: str, param2: int) -> str:
    """Clear description of what this tool does.

    Provide enough detail so the agent knows WHEN and HOW to use this tool.
    The docstring is the primary mechanism for the agent to decide whether to call it.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of what is returned
    """
    logger.info(f"[my_tool_name] params: param1={param1}, param2={param2}")

    # Tool logic here
    result = f"Processed {param1} with {param2}"

    logger.info(f"[my_tool_name] result: {result}")
    return result
```

### Critical Rules

1. **One tool per file**: Each `.py` file in the Tools directory should contain exactly one `@tool` function.
2. **File name = function name**: The file should be named after the tool function (e.g., `my_tool_name.py` contains `def my_tool_name(...)`).
3. **Type hints are required**: All parameters and return types must have type annotations.
4. **Docstring is essential**: The docstring serves as the tool's description for the agent. Write it clearly — it determines when and how the agent will use the tool.
5. **Use logging**: Always log inputs and outputs using the `logger` for debugging.
6. **Tools run in the sandbox**: All `@tool` functions execute in the sandbox container — the same environment where test scripts run. This means the testing environment IS the production environment. You can import any package available in the sandbox.
7. **Pure functions preferred**: Tools should ideally be stateless. If state is needed, use file I/O or external services.
8. **Return serializable types**: Return `str`, `int`, `float`, `bool`, `dict`, or `list` — types that can be serialized in the agent's conversation.

9. **Include `__tool_meta__` by default**: Every new tool should define module-level metadata with `category`, `subcategory`, and `tags` so the External Tools library can classify it automatically.

### Tool Metadata

Add a module-level `__tool_meta__` constant near the top of every new tool file:

```python
__tool_meta__ = {
    "category": "Models & Prediction",
    "subcategory": "Materials Science",
    "tags": ["materials", "dft", "phase-diagram"],
}
```

- `category`: required display category for sidebar grouping; keep this functional, such as `Data & Resources`, `Database & API`, `Models & Prediction`, `Analysis & Workflow`, `Knowledge & Literature`, or `Workspace & Authoring`
- `subcategory`: optional second-level grouping shown as chips; use this for domain placement such as `Materials Science`
- `tags`: optional list of short labels used for fine-grained filtering
- Use short, human-readable strings; avoid IDs or long sentences
- Keep metadata as plain Python literals only, so backend AST parsing can read it safely without importing the tool
- Do not use `Materials Science` as the top-level `category`; use it as `subcategory` instead

### Available Packages (Sandbox Environment)

All `@tool` functions execute in the **sandbox container** — the same environment where test scripts run. The following packages are pre-installed:

- Python standard library (json, os, re, math, datetime, pathlib, etc.)
- `httpx` — HTTP client for API calls
- `pydantic` — Data validation
- `langchain_core` — Required for `@tool` decorator
- `pyyaml` — YAML parsing
- `seekr_sdk` — Provides `web_search`, `web_crawl`, `web_crawl_many` for internet search and page crawling. When writing `@tool` functions that need to search the web or crawl pages, **always prefer `seekr_sdk` over raw `httpx` calls**. See the "Web-Enabled Tool (using seekr_sdk)" example below.

Since tools run in the same sandbox where you test them, **if your test passes in the sandbox, the tool will also work in production**. If a tool needs a package not in this list, install it in the sandbox Dockerfile (docker-compose.yml sandbox service).

### Docstring Writing Guide

The docstring is how the agent decides whether to call a tool. Good docstrings:

- **First line**: A concise summary of what the tool does (this appears in tool listings)
- **Body**: Explain when to use this tool, what scenarios it covers, and any important constraints
- **Args section**: Describe each parameter with its expected format and examples
- **Returns section**: Describe the return value and its format

Make descriptions specific and "pushy" enough that the agent reliably triggers the tool for relevant tasks. For example:

Bad: `"""Calculate a score."""`

Good: `"""根据身高、体重、年龄计算人物综合打分。该工具根据人的身体数据进行综合评估打分，包括BMI健康指数评分和年龄评分。"""`

---

## Mode 1: Creating a New Tool

When the user wants to create a new tool from scratch or convert a script into a tool:

### Step 1: Understand Requirements

Ask the user:
1. What should this tool do? What problem does it solve?
2. What inputs does it need? (parameter names, types, examples)
3. What should it return? (type, format)
4. Does it need external API calls or only local computation?
5. Are there edge cases or error conditions to handle?

If the user already has a script or describes the logic clearly, extract the answers from context.

### Step 2: Write the Tool (as @tool from the start)

**CRITICAL**: Write the code directly as an `@tool` function from the very beginning. Do NOT first write a standalone script and then convert it — this leads to mismatches between tested and saved code.

Based on the requirements, write a complete tool file following the format above. Key considerations:

- Choose a clear, descriptive function name using `snake_case`
- Add `__tool_meta__` before the tool function so it is classified correctly in the UI
- Write a comprehensive docstring
- Add proper error handling (try/except, input validation)
- Log inputs and outputs
- Keep it focused — one tool does one thing well
- If the tool needs web search or crawling, use `seekr_sdk` (available in both backend and sandbox)

### Step 3: Test the @tool in Sandbox

Test the actual `@tool` function (NOT a separate standalone script):

1. Save the tool to `{workspace_dir}/tools_dev/{tool_name}.py`
2. Write a test script `{workspace_dir}/tools_dev/test_{tool_name}.py`:
   ```python
   import sys
   sys.path.insert(0, "{workspace_dir}/tools_dev")
   from {tool_name} import {tool_name}

   # Test cases — this calls the SAME @tool function that will be saved
   result = {tool_name}.invoke({{"param1": "value1", "param2": 42}})
   print(f"Result: {result}")
   ```
3. Run the test in the sandbox and verify the output
4. If there are errors, fix `{workspace_dir}/tools_dev/{tool_name}.py` and re-test

**IMPORTANT**: The test MUST import and invoke the `@tool` function from `tools_dev/{tool_name}.py`. Never test a separate script with different logic — only the actual tool code that will be saved matters.

### Step 4: Review with User

Present the tool code and test results to the user:
- Show the complete tool source code
- Show the test results
- Ask for feedback: "Does this look right? Anything you'd change?"

If the user requests changes, go back to Step 2: modify `tools_dev/{tool_name}.py`, re-test, and review again.

### Step 5: Save the Tool (copy tested file, do NOT rewrite)

Once the user is satisfied:

1. **Copy** the tested file directly: `cp {workspace_dir}/tools_dev/{tool_name}.py {workspace_dir}/tools_staging/{tool_name}.py`
2. Call `propose_tool_save(tool_name="{tool_name}")` to prompt the user to save it permanently

**CRITICAL — TESTED = SAVED**: The file in `tools_staging/` MUST be an exact copy of the tested file from `tools_dev/`. Do NOT rewrite or modify the code between testing and saving. The whole point is that the version the user saw working in tests is exactly what gets saved.

**IMPORTANT**: Always call `propose_tool_save` — never try to write directly to the Tools directory.

---

## Mode 2: Upgrading an Existing Tool

When the user wants to modify, improve, or fix an existing tool:

### Step 1: Identify the Tool

List or read the existing tools to find the one the user wants to upgrade. The existing tools are available at `/app/Tools/` (mounted as the Tools directory). You can:

- Read the tool's source code to understand its current implementation
- Understand what the user wants to change

### Step 2: Copy to Workspace for Development

Copy the existing tool to the session workspace for safe modification:

```bash
cp /app/Tools/{tool_name}.py {workspace_dir}/tools_dev/{tool_name}.py
```

This ensures the original tool remains untouched while you iterate.

### Step 3: Modify and Test

1. Make the requested changes to `{workspace_dir}/tools_dev/{tool_name}.py`
2. Write test scripts to verify both the new behavior AND that existing functionality still works
3. Run tests in the sandbox
4. Iterate with the user until they're satisfied

#### Debugging External API Failures (CRITICAL)

When a tool depends on an external API and it starts failing (e.g., HTTP 404/403/500, empty responses, changed data format):

**DO NOT blindly guess URL variations or probe endpoints.** If the first 1–2 attempts fail, STOP and use `seekr_sdk` to diagnose:

1. **Search for the cause**: `web_search("Dukascopy datafeed API 404 2026")` or `web_search("<service_name> API deprecated")`
2. **Search for alternatives**: `web_search("free gold price API hourly JSON 2026")` or `web_search("<domain> alternative API")`
3. **Verify new API docs**: `web_crawl("<documentation_url>")` to confirm correct endpoints, parameters, and response formats before writing code
4. **Then implement the fix** based on confirmed, working information

**Anti-pattern (NEVER do this):**
```
# Wasting tokens and time guessing URLs:
httpx.get("https://api.example.com/v1/data")   # 404
httpx.get("https://api.example.com/v2/data")   # 404
httpx.get("https://api.example.com/data/v1")   # 404
httpx.get("https://www.example.com/api/data")  # 404
# ... 10 more blind guesses ...
```

**Correct pattern:**
```python
from seekr_sdk import web_search, web_crawl
# First attempt failed with 404 → immediately search for answers
results = web_search("example.com API changes 2026 alternative endpoint")
# Read the relevant documentation
doc = web_crawl("https://docs.newapi.com/gold-price")
# Now implement with confirmed information
```

This applies to **both creating new tools and upgrading existing ones**. External APIs change frequently — always verify availability via search before investing time in code changes.

### Step 4: Side-by-Side Comparison

Before proposing the replacement, show the user a clear comparison:
- What changed and why
- Test results showing the improvement
- Any potential breaking changes or new dependencies

### Step 5: Propose Replacement (copy tested file, do NOT rewrite)

Once the user confirms they're happy:

1. **Copy** the tested file directly: `cp {workspace_dir}/tools_dev/{tool_name}.py {workspace_dir}/tools_staging/{tool_name}.py`
2. Call `propose_tool_save(tool_name="{tool_name}")` to ask the user to replace the original

**CRITICAL — TESTED = SAVED**: Do NOT rewrite the tool between testing and saving. The file in `tools_staging/` must be an exact copy of the tested and approved file from `tools_dev/`.

The system will replace the existing tool in the Tools directory with the new version.

---

## Example Tools for Reference

Here are patterns from existing tools in the system:

### Simple Computation Tool

```python
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def person_physical_score(height: float, weight: float, age: int) -> int:
    """根据身高、体重、年龄计算人物综合打分。

    该工具根据人的身体数据进行综合评估打分，包括BMI健康指数评分和年龄评分。

    Args:
        height: 身高（单位：厘米，如170.0）
        weight: 体重（单位：公斤，如65.0）
        age: 年龄（单位：岁，如25）

    Returns:
        综合得分（满分100分）
    """
    logger.info(f"[person_physical_score] params: height={height}, weight={weight}, age={age}")

    height_m = height / 100
    bmi = weight / (height_m ** 2)

    if 18.5 <= bmi <= 24:
        bmi_score = 40
    elif 24 < bmi <= 28:
        bmi_score = 30
    else:
        bmi_score = 20

    total_score = bmi_score + 30 + 30  # simplified
    logger.info(f"[person_physical_score] result: {total_score}")
    return total_score
```

### API-Calling Tool

```python
import logging
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def check_weather(city: str) -> dict:
    """查询指定城市的天气信息。

    调用公开天气API获取实时天气数据，包括温度、湿度、天气描述等。

    Args:
        city: 城市名称（如"北京"、"Shanghai"）

    Returns:
        包含天气信息的字典，包括 temperature, humidity, description 等字段
    """
    logger.info(f"[check_weather] params: city={city}")
    try:
        resp = httpx.get(
            f"https://api.example.com/weather?city={city}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[check_weather] result: {data}")
        return data
    except Exception as exc:
        logger.error(f"[check_weather] failed: {exc}")
        return {"error": str(exc)}
```

### Web-Enabled Tool (using seekr_sdk)

```python
import logging
from typing import Any, Dict
from langchain_core.tools import tool
from seekr_sdk import web_search, web_crawl

logger = logging.getLogger(__name__)


@tool
def gold_price(query: str = "gold price") -> Dict[str, Any]:
    """查询实时金价（黄金现货/spot）并返回信息。

    当用户询问"gold price / 金价 / 黄金价格 / 实时金价"等需要联网获取最新价格时使用。
    通过 seekr_sdk 搜索互联网获取最新金价数据。

    Args:
        query: 用户查询文本，通常传入 "gold price" 即可。

    Returns:
        包含金价信息的字典
    """
    logger.info(f"[gold_price] query={query!r}")
    results = web_search("current gold price USD per ounce spot")
    snippets = []
    for r in results[:5]:
        snippets.append(f"- {r.get('title', '')}: {r.get('content', '')}")
    summary = "\n".join(snippets)
    logger.info(f"[gold_price] found {len(results)} results")
    return {"ok": True, "search_results": summary, "source_count": len(results)}
```

Key point: `seekr_sdk` functions (`web_search`, `web_crawl`, `web_crawl_many`) are plain Python functions — they work in `@tool` functions and standalone scripts (both run in the sandbox). Always prefer them over raw `httpx` for web search and crawling.

### Aggregation Tool (Calling Other Tools)

```python
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def person_total_score(physical_score: int, social_score: int) -> int:
    """根据身体评分和社会评分计算综合总分。

    该工具将身体评分和社会评分进行加权计算，得出综合总分。
    通常在调用 person_physical_score 和 person_social_score 之后使用。

    Args:
        physical_score: 身体评分（0-100分）
        social_score: 社会评分（0-100分）

    Returns:
        综合总分（满分100分）
    """
    logger.info(f"[person_total_score] params: physical_score={physical_score}, social_score={social_score}")
    total_score = int(physical_score * 0.5 + social_score * 0.5)
    logger.info(f"[person_total_score] result: {total_score}")
    return total_score
```

---

## ScienceClaw Environment Notes

- **Workspace**: Your workspace directory is provided in the system prompt (e.g., `/home/scienceclaw/{session_id}/`). Use `{workspace_dir}/tools_dev/` for development and `{workspace_dir}/tools_staging/` for final versions.
- **Sandbox execution**: Both test scripts AND saved `@tool` functions run in the sandbox container. The testing environment IS the production environment. Use absolute paths.
- **Tools directory**: The permanent Tools directory is at `/app/Tools/`. Never write directly to it — always use `propose_tool_save`.
- **Hot reload not available**: After a tool is saved to Tools/, it will be available in NEW sessions. The current session uses the tools that were loaded when it started.
- **`propose_tool_save` tool**: This is the ONLY way to save a tool. It triggers a UI prompt for the user to confirm. The system copies the file from `{workspace_dir}/tools_staging/{tool_name}.py` to `/app/Tools/{tool_name}.py`.

---

## Retroactive Tool Creation (from a completed task)

Sometimes the agent writes a one-off script during a task and realizes (or the user requests) it should be a permanent tool. This is the "reflect & capture" mode.

**When to trigger:**
- The agent wrote a utility script (write_file + execute) that solved a reusable problem
- The user says "save this as a tool", "make this reusable", or similar
- The system prompt's Step 4 (Reflect) suggests capturing a utility

**How to convert a script to a tool:**

1. **Identify the core function**: Look at the script you just wrote. Extract the reusable logic.
2. **Wrap as @tool**: Rewrite it as a proper `@tool` function following the format above. Parameterize hardcoded values.
3. **Test**: Run the `@tool` function in sandbox to verify it produces the same results.
4. **Save**: Copy to `{workspace_dir}/tools_staging/` → `propose_tool_save`.

**Key principle**: The tool should be MORE general than the original script. If you wrote a script to fetch gold prices from a specific API, the tool should handle any commodity price or at least be clearly named for its specific use case.

---

## Common Pitfalls

1. **Missing type hints**: The `@tool` decorator requires type annotations on all parameters. Without them, the tool won't work correctly.
2. **Bad docstring**: If the docstring is vague, the agent won't know when to call the tool. Be specific.
3. **Forgetting `@tool` decorator**: The function MUST be decorated with `@tool` from `langchain_core.tools`.
4. **Non-serializable return types**: Don't return custom objects, generators, or other non-serializable types.
5. **Importing unavailable packages**: Since tools run in the sandbox, test your tool there first — if it imports fine during testing, it will work in production too.
6. **Writing to Tools/ directly**: Never do this. Always use the workspace → `propose_tool_save` flow.
7. **Tested code ≠ saved code**: NEVER write a standalone script first and then rewrite it as an `@tool`. Always write the `@tool` function first, test that exact function, then copy (not rewrite) it to `tools_staging/`. The tested file must be identical to the saved file.
8. **Using raw httpx for web search/crawl**: When the tool needs to search or crawl the web, always use `seekr_sdk` (`from seekr_sdk import web_search, web_crawl`). Do NOT use `httpx` to directly scrape websites — it cannot render JavaScript and is fragile against website changes.
9. **Blindly guessing URLs when an API fails**: When an external API returns errors (404, 403, etc.), do NOT try multiple URL variations hoping one works. After 1–2 failed attempts, use `web_search` from `seekr_sdk` to find out why the API is failing and what alternatives exist. Blind URL probing wastes tokens, time, and almost never succeeds — search engines exist for a reason.
