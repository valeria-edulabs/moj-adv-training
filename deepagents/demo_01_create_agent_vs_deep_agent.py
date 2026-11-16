"""Demo 1 — same task, same tool: create_agent vs create_deep_agent.

Point to make: create_deep_agent IS create_agent + a pre-built middleware stack
(filesystem, subagents/task, summarization, prompt caching, ...).
Run it and compare the tool-call traces.
"""
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from deepagents import create_deep_agent

from common import MODEL, internet_search, print_trace

from dotenv import load_dotenv
load_dotenv()

TASK = (
    "Compare LangGraph, CrewAI and the OpenAI Agents SDK on: persistence, "
    "human-in-the-loop and multi-agent support. Produce a markdown table and a recommendation."
)

# 1) The agent participants already know
shallow = create_agent(
    MODEL,
    tools=[internet_search],
    system_prompt="You are a research assistant.",
)

# 2) The deep agent: same model, same tool, same prompt
deep = create_deep_agent(
    MODEL,
    tools=[internet_search],
    system_prompt=(
        "You are a research assistant. Plan first with write_todos, keep raw notes in "
        "/notes/*.md, and write the final answer to /report.md before replying."
    ),
    # Planning (write_todos) is opt-in since deepagents 0.7 — it's plain LangChain middleware
    middleware=[TodoListMiddleware()],
)

if __name__ == "__main__":
    inputs = {"messages": [{"role": "user", "content": TASK}]}

    print("=" * 30, "create_agent", "=" * 30)
    print_trace(shallow.invoke(inputs))

    print("\n" + "=" * 30, "create_deep_agent", "=" * 30)
    result = deep.invoke(inputs)
    print_trace(result)  # note: todos + files live in the graph STATE (StateBackend default)
