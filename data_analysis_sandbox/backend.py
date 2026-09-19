"""Backend for Data Analysis Agent with DockerSandboxBackend.

Integrates deepagents.create_deep_agent with DockerSandboxBackend for true container-level
isolated code and shell execution.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data_analysis_sandbox.docker_backend import DockerSandboxBackend
except ImportError:
    from docker_backend import DockerSandboxBackend
from deepagents import create_deep_agent

load_dotenv()
logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).parent.resolve()
CSV_PATH = CURRENT_DIR / "products_stock_data.csv"

SYSTEM_PROMPT = """You are an expert Data Analyst Agent operating inside a secure, isolated Docker container sandbox.
You have access to filesystem and command execution tools provided by FilesystemMiddleware:
- `execute`: Execute shell commands and Python code inside the Docker sandbox.
- `read_file`: Read the contents of any file in the workspace.
- `write_file`: Write text or scripts to files in the workspace.
- `ls`: List files in the sandbox workspace.
- `glob`: Search for files matching a pattern.
- `grep`: Search for text patterns inside files.

### Sandbox Environment & Dataset:
- The dataset `products_stock_data.csv` is preloaded in your workspace at `/workspace/products_stock_data.csv` (and `./products_stock_data.csv`).
- Available pre-installed Python libraries in the container: `pandas`, `plotly`, `numpy`.

### Guidelines for Analysis:
1. **Calculations & Summaries**:
   - Write concise Python code to compute metrics, statistics, or answer queries.
   - Execute it via `execute` (e.g. `python3 -c "import pandas as pd; df = pd.read_csv('products_stock_data.csv'); print(df.describe())"` or write a script with `write_file` and run `python3 script.py`).
   - Print final answers clearly with `print()`.

2. **Plots & Visualizations**:
   - When asked for a plot, chart, or visual distribution, generate an interactive chart using Plotly Express (`px`) or Graph Objects (`go`).
   - You MUST export the figure to `chart.json` using:
     `fig.write_json('chart.json')`
   - Do NOT call `fig.show()`. The user interface will automatically detect `chart.json` and render the interactive Plotly visualization.

3. **Data Tables & Filtered Results**:
   - When asked to show a table, filtered list, or aggregated records:
   - Filter or aggregate the DataFrame into variable `result`.
   - Save the table to `result.json` using:
     `result.to_json('result.json', orient='records')`
   - The user interface will automatically detect `result.json` and render it as an interactive table.

4. **Explanations**:
   - Explain what your code did and provide insights into the results.
   - Confirm that the chart or table has been generated and displayed for the user.

5. **Human-in-the-Loop**:
   - Any `execute` command is reviewed by the human before running in the container.
   - If the user edits the command or rejects execution, adhere respectfully to their instructions.
"""

# Global registry of active thread backends and compiled agents
_backends: Dict[str, DockerSandboxBackend] = {}
_agents: Dict[str, Any] = {}
_memory = MemorySaver()
_last_artifact_timestamps: Dict[str, Dict[str, float]] = {}


def get_or_create_sandbox(thread_id: str) -> tuple[Any, DockerSandboxBackend]:
    """Retrieve or create the agent and Docker sandbox backend for the given thread_id."""
    clean_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:32] or "default"
    
    if clean_thread not in _backends:
        container_name = f"sandbox_da_{clean_thread}"
        workspace_dir = CURRENT_DIR / "sandbox_workspaces" / clean_thread
        workspace_dir.mkdir(parents=True, exist_ok=True)

        backend = DockerSandboxBackend(
            container_name=container_name,
            workspace_dir=workspace_dir,
            timeout=120,
            mem_limit="512m",
            cpus=1.0,
            network="none",
        )

        # Upload the dataset into the container
        if CSV_PATH.exists():
            with open(CSV_PATH, "rb") as f:
                csv_bytes = f.read()
            backend.upload_files([
                ("/workspace/products_stock_data.csv", csv_bytes),
                ("/products_stock_data.csv", csv_bytes),
            ])

        # Initialize the Deep Agent with Docker sandbox backend and HITL interrupt on execute
        llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0.1)
        agent = create_deep_agent(
            model=llm,
            backend=backend,
            checkpointer=_memory,
            system_prompt=SYSTEM_PROMPT,
            interrupt_on={"execute": True},
        )

        _backends[clean_thread] = backend
        _agents[clean_thread] = agent
        _last_artifact_timestamps[clean_thread] = {"chart": 0.0, "result": 0.0}

    return _agents[clean_thread], _backends[clean_thread]


def check_and_extract_artifacts(clean_thread: str, backend: DockerSandboxBackend) -> Optional[dict]:
    """Check if the sandbox container generated a new chart.json or result.json."""
    # Sync if created in container root
    backend.execute("if [ -f /chart.json ]; then cp -f /chart.json /workspace/chart.json; fi; if [ -f /result.json ]; then cp -f /result.json /workspace/result.json; fi")

    workspace = backend.workspace_dir
    chart_file = workspace / "chart.json"
    result_file = workspace / "result.json"

    timestamps = _last_artifact_timestamps.get(clean_thread, {"chart": 0.0, "result": 0.0})

    # Check for newly generated chart.json
    if chart_file.exists():
        mtime = chart_file.stat().st_mtime
        if mtime > timestamps.get("chart", 0.0):
            try:
                with open(chart_file, "r", encoding="utf-8") as f:
                    chart_data = json.load(f)
                timestamps["chart"] = mtime
                _last_artifact_timestamps[clean_thread] = timestamps
                return {
                    "type": "plotly",
                    "data": chart_data,
                }
            except Exception as e:
                logger.warning("Error reading chart.json artifact: %s", e)

    # Check for newly generated result.json
    if result_file.exists():
        mtime = result_file.stat().st_mtime
        if mtime > timestamps.get("result", 0.0):
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                timestamps["result"] = mtime
                _last_artifact_timestamps[clean_thread] = timestamps
                return {
                    "type": "dataframe",
                    "data": result_data,
                }
            except Exception as e:
                logger.warning("Error reading result.json artifact: %s", e)

    return None


def stream(text: str, thread_id: str) -> Generator[Dict[str, Any], None, None]:
    """Stream user prompt updates from the deep agent with Docker sandbox backend."""
    clean_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:32] or "default"
    agent, backend = get_or_create_sandbox(clean_thread)
    config = {"configurable": {"thread_id": clean_thread}}

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates",
    ):
        # If tools ran, check if any rich artifact was generated in the sandbox
        if "tools" in chunk:
            tool_msg = chunk["tools"]["messages"][0]
            artifact = check_and_extract_artifacts(clean_thread, backend)
            if artifact is not None:
                setattr(tool_msg, "artifact", artifact)

        yield chunk


def resume_stream(decision: dict, thread_id: str) -> Generator[Dict[str, Any], None, None]:
    """Resume execution after human approval or edit of the pending sandbox action."""
    clean_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:32] or "default"
    agent, backend = get_or_create_sandbox(clean_thread)
    config = {"configurable": {"thread_id": clean_thread}}

    for chunk in agent.stream(
        Command(resume=decision),
        config=config,
        stream_mode="updates",
    ):
        if "tools" in chunk:
            tool_msg = chunk["tools"]["messages"][0]
            artifact = check_and_extract_artifacts(clean_thread, backend)
            if artifact is not None:
                setattr(tool_msg, "artifact", artifact)

        yield chunk


def reset_thread(thread_id: str) -> None:
    """Reset and clean up Docker sandbox container for a given thread."""
    clean_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:32] or "default"
    if clean_thread in _backends:
        backend = _backends.pop(clean_thread)
        try:
            backend.close()
        except Exception:
            pass
    _agents.pop(clean_thread, None)
    _last_artifact_timestamps.pop(clean_thread, None)


def get_sandbox_status(thread_id: str) -> dict:
    """Return status of the Docker sandbox container for this thread."""
    clean_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:32] or "default"
    if clean_thread in _backends:
        backend = _backends[clean_thread]
        return {
            "active": True,
            "backend_type": "DockerSandboxBackend (BaseSandbox)",
            "container_name": backend.container_name,
            "sandbox_id": backend.id,
            "workspace": str(backend.workspace_dir),
            "network": "none (isolated)",
            "memory": "512m",
        }
    return {
        "active": False,
        "backend_type": "DockerSandboxBackend (BaseSandbox)",
        "container_name": None,
        "sandbox_id": None,
        "network": "none (isolated)",
    }


def save_graph_png() -> None:
    """Export the compiled DeepAgent LangGraph mermaid diagram to PNG."""
    agent, _ = get_or_create_sandbox("graph_export")
    agent.get_graph().draw_mermaid_png(output_file_path=str(CURRENT_DIR / "graph.png"))


if __name__ == "__main__":
    save_graph_png()
    print("Graph saved to graph.png")
