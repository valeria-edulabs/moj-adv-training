"""Demo 6 — Code execution: the `execute` tool appears when the backend can run commands.

LocalShellBackend runs on YOUR machine -> fine for a classroom demo, gated by HITL.
In production swap it for a sandbox backend, same agent code:
    from langchain_daytona import DaytonaSandbox      # or langchain_modal.ModalSandbox,
    from langchain_e2b import E2BSandbox              #    deepagents.backends.langsmith.LangSmithSandbox, ...
"""
import uuid

from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from common import MODEL, print_trace, run_with_approval

agent = create_deep_agent(
    MODEL,
    system_prompt="You are a data analyst. Write Python scripts to files, run them with execute, "
                  "and fix errors until they work.",
    backend=LocalShellBackend(root_dir="./sandbox_ws", virtual_mode=True, timeout=60),
    interrupt_on={"execute": True},   # a human approves every shell command
    checkpointer=MemorySaver(),
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = run_with_approval(agent, {"messages": [{"role": "user", "content":
        "Simulate 10,000 rolls of two dice with only the Python standard library, "
        "and report the distribution of sums as a text histogram."}]}, config)
    print_trace(result)
