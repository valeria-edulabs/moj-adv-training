"""Demo 3 — Subagents: context isolation via the `task` tool.

- research-agent : dict-defined subagent, own prompt, own tools, cheaper model
- critique-agent : dict-defined subagent, NO extra tools (only reads files)
- fact-checker   : a plain create_agent graph wrapped as CompiledSubAgent
                   -> bridge from what participants already know
The main agent only sees each subagent's FINAL message, not its 20 search calls.
"""
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from deepagents import CompiledSubAgent, create_deep_agent

from common import CHEAP_MODEL, MODEL, internet_search, print_trace

from dotenv import load_dotenv
load_dotenv()

research_subagent = {
    "name": "research-agent",
    "description": "Researches ONE focused topic in depth. Give it a single topic per call.",
    "system_prompt": (
        "You are a meticulous researcher. Search, then answer with a concise, "
        "well-cited summary (max 300 words). Your final message is all the caller sees."
    ),
    "tools": [internet_search],
    "model": CHEAP_MODEL,
}

critique_subagent = {
    "name": "critique-agent",
    "description": "Critiques the draft at /report.md: gaps, unsupported claims, structure.",
    "system_prompt": "You are a tough editor. Read /report.md and return a numbered list of concrete fixes.",
    # no "tools" key -> inherits the main agent's tools; built-in file tools are always there
}

fact_checker_graph = create_agent(
    CHEAP_MODEL,
    tools=[internet_search],
    system_prompt="Verify the given claims. Reply with each claim marked TRUE/FALSE/UNSURE plus a source.",
)
fact_checker = CompiledSubAgent(
    name="fact-checker",
    description="Verifies a list of factual claims against the web.",
    runnable=fact_checker_graph,
)

agent = create_deep_agent(
    MODEL,
    system_prompt=(
        "You are a lead analyst. Delegate each sub-topic to research-agent IN PARALLEL "
        "(several task calls in one turn). Write /report.md, ask critique-agent for feedback, "
        "use fact-checker on key numbers, then revise /report.md and reply with it."
    ),
    subagents=[research_subagent, critique_subagent, fact_checker],
    middleware=[TodoListMiddleware()],
)

if __name__ == "__main__":
    result = agent.invoke({"messages": [{"role": "user", "content":
        "Write a briefing on the state of small open-weight LLMs: top 3 model families, "
        "license terms, and typical hardware needed."}]})
    print_trace(result)  # look for `task` calls with subagent_type=...
