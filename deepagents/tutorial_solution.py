"""Reference solution for TUTORIAL.md (steps 1-6 combined)."""
import uuid
from pathlib import Path

from langchain.agents.middleware import TodoListMiddleware
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data

from common import CHEAP_MODEL, MODEL, internet_search, print_trace, run_with_approval

# --- Step 6: a skill on disk -------------------------------------------------
Path("skills/swot").mkdir(parents=True, exist_ok=True)
Path("skills/swot/SKILL.md").write_text("""---
name: swot
description: Produce a SWOT analysis for a product or company. Use when the user asks for SWOT.
---
Output four headed sections (Strengths, Weaknesses, Opportunities, Threats), 3-5 bullets each,
every bullet backed by a fact from research. End with one 'So what?' sentence.
""")


# --- Step 4: a side-effecting tool to gate ------------------------------------
@tool
def publish_to_slack(channel: str, summary: str) -> str:
    """Publish a report summary to a Slack channel."""
    return f"(pretend) posted to #{channel}"


# --- Step 3: subagents --------------------------------------------------------
researcher = {
    "name": "competitor-researcher",
    "description": "Researches ONE competitor product. Pass the product name and the criteria.",
    "system_prompt": (
        "Research the given product against the given criteria using internet_search. "
        "Return a structured summary of at most 250 words with source URLs."
    ),
    "tools": [internet_search],
    "model": CHEAP_MODEL,
}
reviewer = {
    "name": "reviewer",
    "description": "Critiques a report file. Pass the report path.",
    "system_prompt": "Read the report and return a numbered list of concrete improvements.",
}

# --- Steps 2 + 5: backends ----------------------------------------------------
store = InMemoryStore()
store.put(  # seed long-term memory (key is relative to the /memories/ route)
    ("me",), "/AGENTS.md",
    create_file_data("# Preferences\n- Always include a pricing table in EUR.\n"),
)

backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/reports/": FilesystemBackend(root_dir="./reports", virtual_mode=True),
        "/memories/": StoreBackend(namespace=lambda rt: ("me",)),
        "/skills/": FilesystemBackend(root_dir="./skills", virtual_mode=True),
    },
)

agent = create_deep_agent(
    MODEL,
    tools=[internet_search, publish_to_slack],
    system_prompt=(
        "You are a competitive-analysis lead.\n"
        "1. Plan with write_todos.\n"
        "2. Launch one competitor-researcher task PER product, all in the same turn.\n"
        "3. Keep raw notes in /notes/. Write the final report to /reports/<slug>.md.\n"
        "4. Ask reviewer to critique it, apply the fixes.\n"
        "5. Publish a 3-line summary with publish_to_slack to #product.\n"
        "When the user states a lasting preference, append it to /memories/AGENTS.md."
    ),
    subagents=[researcher, reviewer],
    middleware=[TodoListMiddleware()],
    backend=backend,
    memory=["/memories/AGENTS.md"],
    skills=["/skills/"],
    interrupt_on={
        "publish_to_slack": True,
        "write_file": {"allowed_decisions": ["approve", "reject"]},
    },
    checkpointer=MemorySaver(),
    store=store,
)


def ask(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    result = run_with_approval(agent, {"messages": [{"role": "user", "content": text}]}, config)
    print_trace(result)


if __name__ == "__main__":
    ask("From now on, also score each product 1-5 on security.", "thread-A")
    ask("Competitive analysis of Notion vs Obsidian vs Coda for a 20-person startup: "
        "pricing, collaboration, offline, AI features. Include a SWOT for Coda.",
        f"thread-B-{uuid.uuid4()}")
