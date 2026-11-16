"""Demo 4 — Human-in-the-loop with interrupt_on (needs a checkpointer).

Built-in tools (write_file, edit_file, execute, ...) and your own tools can both be gated.
Run it and try: approve / edit (change the recipient) / reject (with a reason).
"""
import uuid

from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

from common import MODEL, print_trace, run_with_approval


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"(pretend) email sent to {to}"


@tool
def delete_customer(customer_id: str) -> str:
    """Permanently delete a customer record."""
    return f"(pretend) deleted {customer_id}"


agent = create_deep_agent(
    MODEL,
    tools=[send_email, delete_customer],
    interrupt_on={
        "send_email": True,                                         # approve / edit / reject
        "delete_customer": {"allowed_decisions": ["approve", "reject"]},  # no editing
        "write_file": True,                                         # gate a BUILT-IN tool too
        "read_file": False,
    },
    checkpointer=MemorySaver(),  # required: the graph pauses and resumes from the checkpoint
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = run_with_approval(agent, {"messages": [{"role": "user", "content":
        "Customer C-42 asked to close their account. Draft a goodbye email to c42@example.com, "
        "save the draft to /drafts/c42.md, send it, then delete the customer."}]}, config)
    print_trace(result)
