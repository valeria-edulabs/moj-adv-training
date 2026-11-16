# Hands-on: Keep the context small with a subagent

**Goal:** Build two deep agents that answer the same question about a long text. One reads the text itself. The other sends the reading to a subagent. Then compare how many tokens each main agent had to hold at its peak.

**Time:** about 30 minutes
**File to create:** `deepagents/hands_on_subagents.py`

**Before you start:** `pip install -U deepagents requests`, and set the API key for the model in `common.py` (`MODEL`).

---

## Step 1: A tool that returns a long text

Download *The Winter's Tale* (about 40,000 tokens) and wrap it in a tool.

```python
import requests
from langchain_core.tools import tool

raw = requests.get("https://www.gutenberg.org/cache/epub/1539/pg1539.txt", timeout=30).text
start = raw.index("\n", raw.index("*** START")) + 1
PLAY = raw[start:raw.index("*** END")].strip()   # drop the Gutenberg license

@tool
def read_play() -> str:
    """Return the full text of The Winter's Tale by William Shakespeare. It's very long."""
    return PLAY
```

## Step 2: Measure the peak context

Write a helper, `peak_context(result)`, that returns the largest `usage_metadata["input_tokens"]` over all the `AIMessage`s in `result["messages"]`. This is the most the model ever had to read at once.

## Step 3: The baseline, an agent without a subagent

```python
QUESTION = "Summarize each of the five acts of the play in one sentence."
TEXT_ONLY = "Answer only from the text that read_play returns, not from memory. Read as much of it as you need."
```

Use `create_deep_agent(...)` to make an agent with `tools=[read_play]` and `system_prompt=TEXT_ONLY`. Invoke it with `QUESTION`, then print the trace with `print_trace` (from `common.py`) and the peak context.

> Why `TEXT_ONLY`? The model already knows this famous play. Without that instruction it may answer from memory and never read the text, and then there is nothing to measure.

## Step 4: The same task with a subagent

A subagent is defined as a plain dict:

```python
reader_subagent = {
    "name": "reader_subagent",
    "description": "...",       # TODO: the main agent reads this to decide when to call it
    "system_prompt": "...",     # TODO: start from TEXT_ONLY and ask for a 1–2 sentence reply
    "tools": [read_play],
}
```

Make a second agent that:
- gets `subagents=[reader_subagent]`
- does **not** get `read_play` itself
- has a system prompt telling it to send **each act** to `reader_subagent`

Invoke it with the same `QUESTION`. In the trace you should see several `task` calls, one for each act.

## Step 5: Compare

```python
print(f"Without a subagent: {peak_context(result_without):,} tokens")
print(f"With a subagent:    {peak_context(result_with):,} tokens")
```

**Expected:** the main agent with a subagent peaks at a small fraction of the baseline. The subagent still reads the play, but in its **own** context. The main agent only sees the short answers.

---

## Discuss

1. Did the total cost go up or down? (Hint: the play is now read once per act.) When is that trade-off worth it?
2. What happens if the subagent's `description` is vague? Try it.
3. Change the subagent's system prompt so it replies in a whole paragraph. How does the main agent's peak context change?

## Bonus

- Give the subagent a cheaper model: add `"model": CHEAP_MODEL` to the dict.
- Remove the instruction to send *each act* separately. Does the main agent still split the work?
