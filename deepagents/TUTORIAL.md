# Hands-on: Build a Competitive-Analysis Deep Agent (≈90 min)

**Goal:** turn a plain `create_agent` into a deep agent that researches several
competitors in parallel, writes a real report to disk, asks for approval before
publishing, and remembers your preferences between sessions.

**You'll practice:** planning · virtual filesystem · backends · subagents ·
human-in-the-loop · long-term memory · skills.

```bash
pip install -U deepagents langchain-anthropic tavily-python
export ANTHROPIC_API_KEY=...   TAVILY_API_KEY=...
```
Work in `my_agent.py`. Reuse `internet_search`, `print_trace`, `run_with_approval` from `common.py`.
Reference solution: `tutorial_solution.py`.

---

## Step 0 — Baseline with `create_agent` (10 min)
Build a `create_agent` with `internet_search` and ask:
> "Do a competitive analysis of Notion vs Obsidian vs Coda for a 20-person startup:
> pricing, collaboration, offline, AI features. Save a report."

✅ **Checkpoint:** note how many tool calls it made, whether it "saved" anything,
and how long the final answer is. Keep this output — you'll compare at the end.

## Step 1 — Swap to `create_deep_agent` + planning (10 min)
- Replace `create_agent` with `create_deep_agent` (same model, tools, prompt).
- Add `middleware=[TodoListMiddleware()]`.
- Tell it in the system prompt to plan with `write_todos` first.

✅ **Checkpoint:** print `result["todos"]` and `result["files"]`. Where did the "saved" report go?
❓ *Discuss:* why is the file not on your disk?

## Step 2 — Real files with a `CompositeBackend` (15 min)
- `/` → `StateBackend()` (scratch notes stay in state)
- `/reports/` → `FilesystemBackend(root_dir="./reports", virtual_mode=True)`
- Prompt: raw notes go in `/notes/`, the final report in `/reports/<slug>.md`.

✅ **Checkpoint:** the report exists in `./reports/` on disk; notes do not.

## Step 3 — Parallel research subagents (20 min)
- Add a `competitor-researcher` subagent: own `system_prompt`, `tools=[internet_search]`,
  a cheaper `model`. Its final message must be a ≤250-word structured summary.
- Prompt the main agent: *one `task` per competitor, all in the same turn*.
- Add a `reviewer` subagent (no tools) that critiques `/reports/...` before you finish.

✅ **Checkpoint:** in the trace, find the parallel `task` calls.
Compare the main agent's message count with Step 1 — that's context isolation.

## Step 4 — Human approval before publishing (15 min)
- Add a `publish_to_slack(channel: str, summary: str)` tool (fake it — just return a string).
- `interrupt_on={"publish_to_slack": True, "write_file": {"allowed_decisions": ["approve", "reject"]}}`
- Add `checkpointer=MemorySaver()` and a `thread_id`; run with `run_with_approval`.

✅ **Checkpoint:** *edit* the channel name on approval, and *reject* one write with a reason.
Check that the agent adapts to your rejection message.

## Step 5 — Long-term memory (10 min)
- Add a route `/memories/` → `StoreBackend(namespace=lambda rt: ("me",))`,
  pass `store=InMemoryStore()`, and `memory=["/memories/AGENTS.md"]`.
- Seed `AGENTS.md` once (see solution) with "always include a pricing table in EUR".
- Turn 1 (thread A): "From now on, also score each product 1-5 on security."
- Turn 2 (**new** thread B): run a fresh analysis.

✅ **Checkpoint:** thread B uses EUR **and** the security score without being told.

## Step 6 (stretch) — Add a skill (10 min)
Create `skills/swot/SKILL.md` (frontmatter `name: swot`, a `description`, and a SWOT template),
route `/skills/` to a `FilesystemBackend`, and pass `skills=["/skills/"]`.
Ask for "a SWOT for Coda" and check in the trace that the agent `read_file`s the skill only then.

---

## Wrap-up discussion
1. Which of the 6 additions made the biggest quality difference? Which cost the most tokens?
2. When would you **not** use a deep agent? (short, latency-sensitive, single-tool tasks)
3. What would you change for production? (Postgres checkpointer/store, a real sandbox,
   LangSmith tracing, `permissions=` on the filesystem)
