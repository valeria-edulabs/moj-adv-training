"""Demo 5 — Memory (AGENTS.md, always in the prompt) vs Skills (SKILL.md, loaded on demand).

The script creates ./agent_home/ with:
    AGENTS.md                       -> memory: house rules, always loaded
    skills/sql-reviewer/SKILL.md    -> skill: only name+description in the prompt;
                                       the agent read_file's the body when it's relevant
"""
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from common import MODEL, print_trace

from dotenv import load_dotenv
load_dotenv()

HOME = Path("./agent_home")

AGENTS_MD = """# Team conventions
- We use PostgreSQL 16.
- Answer in English, be concise, always end with a 'Next steps' line.
- If the user teaches you a new convention, append it to /AGENTS.md.
"""

SKILL_MD = """---
name: sql-reviewer
description: Review SQL queries for correctness, performance and security. Use whenever the user shares SQL.
---
# SQL review checklist
1. SELECT * in production code -> list columns explicitly.
2. Missing WHERE on UPDATE/DELETE -> block it.
3. String-concatenated params -> SQL injection, use bind params.
4. Filters/joins on non-indexed columns -> suggest an index.
5. Output format: a table | issue | severity | fix |, then the corrected query.
"""


def seed():
    (HOME / "skills/sql-reviewer").mkdir(parents=True, exist_ok=True)
    (HOME / "AGENTS.md").write_text(AGENTS_MD)
    (HOME / "skills/sql-reviewer/SKILL.md").write_text(SKILL_MD)


seed()
agent = create_deep_agent(
    MODEL,
    backend=FilesystemBackend(root_dir=str(HOME), virtual_mode=True),
    memory=["/AGENTS.md"],    # injected into the system prompt every run
    skills=["/skills/"],      # a directory of skill folders (progressive disclosure)
)

if __name__ == "__main__":
    print_trace(agent.invoke({"messages": [{"role": "user", "content":
        "Review this: query = \"SELECT * FROM orders WHERE email = '\" + email + \"'\"\n"
        "Also, from now on: all timestamps must be timestamptz."}]}))
    print("\nAGENTS.md after the run:\n", (HOME / "AGENTS.md").read_text())
