"""Shared helpers for the Deep Agents demos.

Setup:
    pip install -U deepagents langchain-anthropic tavily-python
    export ANTHROPIC_API_KEY=...
    export TAVILY_API_KEY=...        # optional: without it, search returns a stub
    export DEMO_MODEL=anthropic:claude-sonnet-5-5   # optional override
"""
import os
from typing import Literal

from langchain_core.tools import tool
from langgraph.types import Command

MODEL = os.getenv("DEMO_MODEL", "google_genai:gemini-3.5-flash-lite")
CHEAP_MODEL = os.getenv("DEMO_CHEAP_MODEL", "google_genai:gemini-3.5-flash-lite")


@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> dict:
    """Search the web and return a list of results (title, url, content)."""
    key = os.getenv("TAVILY_API_KEY")
    if not key:  # lets the demos run in class without a search key
        return {"results": [{"title": "stub", "url": "-", "content": f"(no TAVILY_API_KEY) fake result for: {query}"}]}
    from tavily import TavilyClient

    return TavilyClient(api_key=key).search(query, max_results=max_results, topic=topic)


def file_text(file_data) -> str:
    """Files in agent state are FileData dicts; content may be a str or list of lines."""
    content = file_data.get("content", file_data) if isinstance(file_data, dict) else file_data
    return "\n".join(content) if isinstance(content, list) else str(content)


def print_trace(result: dict) -> None:
    """Print every tool call the agent made, then the final answer, todos and files."""
    print("\n--- tool calls ---")
    for msg in result["messages"]:
        for call in getattr(msg, "tool_calls", None) or []:
            args = str(call["args"])
            print(f"  {call['name']:<14} {args[:110]}{'…' if len(args) > 110 else ''}")
    if result.get("todos"):
        print("\n--- todos ---")
        for t in result["todos"]:
            print(f"  [{t['status']:<11}] {t['content']}")
    if result.get("files"):
        print("\n--- files in agent state ---")
        for path in result["files"]:
            print("  ", path)
    print("\n--- final answer ---")
    print(result["messages"][-1].content)


def run_with_approval(agent, inputs, config) -> dict:
    """Invoke the agent and ask a human (stdin) to decide on every interrupt."""
    result = agent.invoke(inputs, config=config)
    while result.get("__interrupt__"):
        value = result["__interrupt__"][0].value
        decisions = []
        for req, review in zip(value["action_requests"], value["review_configs"]):
            print(f"\n⚠️  Agent wants to call {req['name']} with:\n   {req['args']}")
            allowed = review["allowed_decisions"]
            choice = input(f"   decision {allowed}: ").strip() or "approve"
            if choice == "reject":
                reason = input("   reason: ")
                decisions.append({"type": "reject", "message": reason})
            elif choice == "edit":
                new_args = eval(input("   new args as python dict: "))  # demo only!
                decisions.append({"type": "edit", "edited_action": {"name": req["name"], "args": new_args}})
            else:
                decisions.append({"type": "approve"})
        result = agent.invoke(Command(resume={"decisions": decisions}), config=config)
    return result
