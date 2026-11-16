"""Demo — Tool output offloading (a.k.a. large tool result eviction).

A tool returns a HUGE result (~2,000 log lines, ~45k tokens).
Deep Agents' FilesystemMiddleware notices it is over the threshold (20k tokens by default)
and, instead of putting it in the context window:

  1. writes the full output to a file:  /large_tool_results/<tool_call_id>
  2. replaces the ToolMessage with a short head+tail preview + the file path
  3. the agent then uses grep / read_file (with offset+limit) to dig into only what it needs

We use a FilesystemBackend so the offloaded file shows up on disk under ./offload_workspace.
"""
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from common import MODEL, print_trace

from dotenv import load_dotenv
load_dotenv()

WORKSPACE = Path("./offload_workspace")


@tool
def fetch_server_logs(service: str) -> str:
    """Fetch today's raw logs for a service. Returns the full log text."""
    rng = random.Random(42)  # deterministic -> same output every run
    start = datetime(2026, 11, 16, 8, 0, 0)
    infos = ["request handled in {}ms", "cache hit for key user:{}", "health check ok",
             "db pool size={}", "GET /api/items/{} 200"]
    errors = {  # needles hidden in the haystack
        412: "ERROR payment-gateway timeout after 30000ms (order 88231)",
        977: "ERROR db connection refused: too many clients",
        1544: "ERROR NullPointerException in CartService.applyCoupon()",
    }
    lines = []
    for i in range(2000):
        ts = (start + timedelta(seconds=7 * i)).isoformat()
        msg = errors.get(i) or "INFO  " + rng.choice(infos).format(rng.randint(1, 9999))
        lines.append(f"{ts} [{service}] pod-{rng.randint(1, 6)} {msg} trace={rng.getrandbits(64):016x}")
    return "\n".join(lines)


def main():
    shutil.rmtree(WORKSPACE, ignore_errors=True)  # fresh start for every demo run

    agent = create_deep_agent(
        MODEL,
        tools=[fetch_server_logs],
        system_prompt="You are an SRE assistant.",
        backend=FilesystemBackend(root_dir=str(WORKSPACE), virtual_mode=True),
    )
    result = agent.invoke({"messages": [{"role": "user", "content":
        "Fetch today's logs for the 'checkout' service and list every ERROR with its timestamp."}]})

    print_trace(result)

    # --- what actually landed in the context window? ---
    raw_size = len(fetch_server_logs.invoke({"service": "checkout"}))
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage) and msg.name == "fetch_server_logs":
            print("\n=== what the MODEL saw as the fetch_server_logs result ===")
            print(msg.content)
            print(f"=== raw tool output: {raw_size:,} chars  ->  in context: {len(msg.content):,} chars ===")

    # --- and where did the full output go? ---
    print("\n--- offloaded files on disk ---")
    for path in sorted((WORKSPACE / "large_tool_results").glob("*")):
        print(f"  {path}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
