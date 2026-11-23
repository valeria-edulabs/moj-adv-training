"""Demo 2 — Where do the agent's files live? Backends.

A) StateBackend (default)   : files live in LangGraph state, scoped to one thread
B) FilesystemBackend        : files are real files on disk (sandboxed to root_dir)
C) CompositeBackend         : route /memories/ to real files (./memories) -> survives across threads and runs
"""
import uuid
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

from common import MODEL, file_text, print_trace

from dotenv import load_dotenv
load_dotenv()


def thread():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def demo_state_backend():
    print("\n### A) StateBackend — seed a file through the input, read results from output")
    agent = create_deep_agent(MODEL)  # backend defaults to StateBackend()
    result = agent.invoke({
        "messages": [{"role": "user", "content": "Read /data/sales.csv and write a 3-line summary to /summary.md"}],
        "files": {"/data/sales.csv": create_file_data("month,revenue\nJan,100\nFeb,140\nMar,90\n")},
    })
    print_trace(result)
    print("\n/summary.md ->\n", file_text(result["files"]["/summary.md"]))


def demo_filesystem_backend():
    print("\n### B) FilesystemBackend — the agent edits real files under ./workspace")
    agent = create_deep_agent(
        MODEL,
        backend=FilesystemBackend(root_dir="./workspace", virtual_mode=True),  # '/' == ./workspace
    )
    print_trace(agent.invoke({"messages": [{"role": "user", "content":
        "Create /hello.py that prints the first 10 Fibonacci numbers, then ls / to confirm."}]}))
    print("\n(check ./workspace/hello.py on your disk)")


def demo_long_term_memory():
    print("\n### C) CompositeBackend — scratch in state, /memories/ in real files under ./memories")
    agent = create_deep_agent(
        MODEL,
        system_prompt="Save durable user preferences to /memories/preferences.md. "
                      "Always follow the saved user preferences when answering.",
        backend=CompositeBackend(
            default=StateBackend(),
            # /memories/preferences.md  ->  ./memories/preferences.md on disk
            # (for production you'd typically use StoreBackend + PostgresStore instead)
            routes={"/memories/": FilesystemBackend(root_dir="./agent_home/memories", virtual_mode=True)},
        ),
        checkpointer=MemorySaver(),
    )
    agent.invoke({"messages": [{"role": "user", "content":
        "Remember: I prefer answers in bullet points and examples in Python."}]}, config=thread())

    # brand-new thread: conversation history is empty, but /memories/ is still there
    agent.invoke({"messages": [{"role": "user", "content":
        "Explain how bubble sort works."}]}, config=thread())



if __name__ == "__main__":
    # demo_state_backend()
    # demo_filesystem_backend()
    demo_long_term_memory()
