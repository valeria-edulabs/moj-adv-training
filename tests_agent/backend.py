import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends import FilesystemBackend

# Load environment variables (e.g. GOOGLE_API_KEY, LANGCHAIN_API_KEY)
load_dotenv()


SYSTEM_PROMPT = """You are a Principal Software Quality Assurance & Test Engineering Agent running an automated Nightly Test Audit.
Your objective is to thoroughly audit the provided Python codebase and its existing unit tests to evaluate test coverage, quality, maintainability, and reliability.

### Available Filesystem Tools:
You have access to filesystem tools provided via FilesystemMiddleware:
- `ls`: List files and subdirectories in a directory path
- `read_file`: Read the content of any file
- `glob`: Find files matching pattern (e.g. `**/*.py`, `**/test_*.py`)
- `grep`: Search for code patterns, function definitions, or assertions across files
- `write_file`: Write text content to a file path

### AUDIT WORKFLOW:
1. **Explore the Code Directory**:
   - Inspect directory contents to understand project structure.
   - Locate and read all primary Python implementation files (`.py`).
   - Understand the functions, classes, business logic, error handling, and execution paths.

2. **Explore Existing Unit Tests**:
   - If a specific tests directory is provided, inspect and read all test files in it.
   - If no separate tests directory is provided, search for test files (e.g., `test_*.py`, `*_test.py`, `tests/`) within the codebase.
   - Read and analyze the test implementations, fixtures, assertions, and mock usage.

3. **In-Depth Analysis**:
   - **Missing Tests**: Identify critical paths, functions, classes, branches, edge cases, and exceptions that have zero or insufficient test coverage.
   - **Test Quality Assessment**: Evaluate existing tests for flakiness, over-mocking, testing implementation details instead of public behavior, weak assertions (e.g. `assert result is not None`), and lack of test isolation.
   - **Suggestions for Improvement**: Recommend specific improvements (e.g., pytest parametrization, reusable fixtures, property-based tests, boundary value checks, mocking best practices).
   - **Actionable Inventory**:
     * **Tests to PRESERVE**: High-value, robust tests that should be kept as-is.
     * **Tests to DELETE**: Obsolete, duplicate, trivial, or brittle tests that hinder refactoring.
     * **Tests to CREATE**: Concrete new test functions required (detail test name, target function, scenario, and expected assertion).
     * **Tests to EDIT**: Existing tests that need updates (describe necessary changes such as stronger assertions or corrected expectations).

4. **Write the Report to Disk**:
   - Produce a comprehensive, well-structured, professional Markdown report.
   - You MUST call the `write_file` tool to save the COMPLETE markdown report into the requested `report_path`.
   - In your final response, provide an executive summary and confirm the exact file path where the report was saved.
"""


def get_llm(model_name: str = "gemini-flash-lite-latest", model_provider: str = "google_genai"):
    """
    Initializes the chat model using LangChain's init_chat_model.
    Demonstrates dynamic provider and model configuration.
    """
    return init_chat_model(model_name, model_provider=model_provider, temperature=0.1)


def create_test_auditor_agent(
    model_name: str = "gemini-flash-lite-latest",
    model_provider: str = "google_genai",
    root_dir: str = "/",
    virtual_mode: bool = True
):
    """
    Creates a LangChain agent equipped with FilesystemMiddleware and FilesystemBackend.
    Using virtual_mode=True is the recommended best practice for sandboxing and security.
    """
    llm = get_llm(model_name=model_name, model_provider=model_provider)
    
    # Sandboxed FilesystemBackend preventing directory traversal (blocks .., ~, outside root)
    backend = FilesystemBackend(root_dir=root_dir, virtual_mode=virtual_mode)
    
    # FilesystemMiddleware exposes filesystem tools to the model
    fs_middleware = FilesystemMiddleware(
        backend=backend,
        tools=["read_file", "ls", "glob", "grep", "write_file"],
        # tool_token_limit_before_evict=200
    )
    
    agent = create_agent(
        model=llm,
        middleware=[fs_middleware],
        system_prompt=SYSTEM_PROMPT
    )
    return agent


def run_test_audit(
    code_dir: str,
    tests_dir: Optional[str] = None,
    report_path: Optional[str] = None,
    job_options: Optional[Dict[str, Any]] = None,
    model_name: str = "gemini-flash-lite-latest"
) -> Generator[Dict[str, Any], None, None]:
    """
    Executes a test audit job over the specified code directory and tests directory.
    Yields real-time events for UI progress display.
    """
    code_dir_abs = os.path.abspath(code_dir)
    if not os.path.exists(code_dir_abs):
        yield {"type": "error", "message": f"Code directory does not exist: {code_dir_abs}"}
        return

    tests_dir_abs = os.path.abspath(tests_dir) if tests_dir and tests_dir.strip() else ""
    if tests_dir_abs and not os.path.exists(tests_dir_abs):
        yield {"type": "error", "message": f"Tests directory does not exist: {tests_dir_abs}"}
        return

    # Default report path if not provided
    if not report_path or not report_path.strip():
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(reports_dir, f"test_audit_report_{timestamp}.md")
    else:
        report_path = os.path.abspath(report_path)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

    job_options = job_options or {}
    test_framework = job_options.get("test_framework", "pytest")
    audit_focus = job_options.get("audit_focus", "Comprehensive Audit (Coverage, Quality, Edge Cases)")
    extra_notes = job_options.get("notes", "")

    # Calculate sandbox root and virtual paths for virtual_mode=True
    paths_to_contain = [code_dir_abs]
    if tests_dir_abs:
        paths_to_contain.append(tests_dir_abs)
    paths_to_contain.append(os.path.dirname(report_path))
    try:
        common_root = os.path.commonpath(paths_to_contain)
    except ValueError:
        common_root = "/"

    def to_virtual_path(abs_path: str) -> str:
        if not abs_path:
            return ""
        rel = os.path.relpath(abs_path, common_root).replace(os.sep, "/")
        return "/" if rel == "." else f"/{rel}"

    virtual_code_dir = to_virtual_path(code_dir_abs)
    virtual_tests_dir = to_virtual_path(tests_dir_abs) if tests_dir_abs else ""
    virtual_report_path = to_virtual_path(report_path)

    yield {
        "type": "status",
        "message": f"Initializing agent with sandboxed Filesystem Middleware (virtual_mode=True, root: `{common_root}`)"
    }

    try:
        agent = create_test_auditor_agent(
            model_name=model_name,
            model_provider="google_genai",
            root_dir=common_root,
            virtual_mode=True
        )
    except Exception as e:
        yield {"type": "error", "message": f"Failed to initialize agent: {str(e)}"}
        return

    # Construct the instruction prompt for this specific job
    user_prompt = f"""Please perform an automated Nightly Test Audit for the following configuration:

- **Root Sandbox Directory**: `{common_root}` (mapped to virtual `/`)
- **Source Code Directory**: `{virtual_code_dir}`
- **Unit Tests Directory**: `{"`" + virtual_tests_dir + "`" if virtual_tests_dir else "Not separately specified (inspect `" + virtual_code_dir + "` for tests)"}`
- **Report Destination Path**: `{virtual_report_path}`
- **Preferred Test Framework**: `{test_framework}`
- **Audit Focus / Depth**: `{audit_focus}`
- **Additional Instructions**: `{extra_notes if extra_notes else "None"}`

### Instructions:
1. You are operating in a secured virtual filesystem where `/` is the sandbox root (`{common_root}`).
   Always pass virtual paths starting with `/` (such as `{virtual_code_dir}` or `{virtual_report_path}`) to filesystem tools (`ls`, `read_file`, `glob`, `grep`, `write_file`).
2. Start by listing files in `{virtual_code_dir}` and examine the implementation files using `read_file` or `grep`.
3. Locate and examine all unit tests (in `{virtual_tests_dir if virtual_tests_dir else virtual_code_dir}`).
4. Assess:
   - Missing tests & coverage gaps.
   - Test quality & reliability (fixtures, assertions, mocks, potential flakiness).
   - Concrete suggestions for improvement.
   - Comprehensive actionable inventory: PRESERVE, DELETE, CREATE, EDIT.
5. Use the `write_file` tool to save the complete Markdown report to `{virtual_report_path}`.
6. In your final response, provide an executive summary and confirm that `{virtual_report_path}` was saved.
"""

    yield {
        "type": "status",
        "message": "Starting audit run. The agent is exploring files via Filesystem Middleware..."
    }

    full_response_text = ""
    report_saved_by_tool = False

    try:
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_prompt}]},
            stream_mode="updates"
        ):
            if "model" in chunk:
                model_msg = chunk["model"]["messages"][0]
                
                # Report any tool calls initiated by the agent
                if getattr(model_msg, "tool_calls", None):
                    for tc in model_msg.tool_calls:
                        tool_name = tc.get("name", "unknown")
                        tool_args = tc.get("args", {})
                        if tool_name == "write_file":
                            report_saved_by_tool = True
                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "args": tool_args
                        }

                # Stream model text content
                if getattr(model_msg, "content", None):
                    text_content = ""
                    if isinstance(model_msg.content, str):
                        text_content = model_msg.content
                    elif isinstance(model_msg.content, list):
                        for part in model_msg.content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_content += part.get("text", "")
                            elif isinstance(part, str):
                                text_content += part
                    if text_content:
                        full_response_text += text_content
                        yield {
                            "type": "content",
                            "delta": text_content,
                            "full": full_response_text
                        }

            elif "tools" in chunk:
                tool_msg = chunk["tools"]["messages"][0]
                yield {
                    "type": "tool_response",
                    "content": tool_msg.content
                }

    except Exception as e:
        yield {"type": "error", "message": f"Error during agent execution: {str(e)}"}
        return

    # Post-execution verification of report file
    final_report_content = ""
    if os.path.exists(report_path) and os.path.getsize(report_path) > 0:
        with open(report_path, "r", encoding="utf-8") as f:
            final_report_content = f.read()
    else:
        # Fallback: if the LLM provided the report in text but forgot to invoke write_file,
        # save the full response text as the report
        if full_response_text.strip():
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(full_response_text.strip())
            final_report_content = full_response_text.strip()
            yield {
                "type": "status",
                "message": f"Report successfully written to `{report_path}` (fallback persist)."
            }

    yield {
        "type": "complete",
        "report_path": report_path,
        "report_content": final_report_content,
        "summary": full_response_text
    }


def list_saved_reports(reports_dir: Optional[str] = None) -> list[dict]:
    """
    Returns a list of saved markdown audit reports sorted by modification time.
    """
    if not reports_dir:
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    
    if not os.path.exists(reports_dir):
        return []

    reports = []
    for file in os.listdir(reports_dir):
        if file.endswith(".md"):
            full_path = os.path.join(reports_dir, file)
            stats = os.stat(full_path)
            reports.append({
                "filename": file,
                "path": full_path,
                "size_kb": round(stats.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

    reports.sort(key=lambda r: r["modified"], reverse=True)
    return reports


def save_graph_png():
    agent = create_test_auditor_agent()
    agent.get_graph().draw_mermaid_png(output_file_path="graph.png")

if __name__ == '__main__':
    save_graph_png()