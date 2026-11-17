from langchain.agents.middleware import ToolCallLimitMiddleware
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.chat_models import init_chat_model

load_dotenv()

# llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")
llm = init_chat_model("google_genai:gemini-3.5-flash-lite")


memory = MemorySaver()

@tool
def calculate_income_tax(annual_income: float):
    """Calculate annual income tax based on annual income"""
    # (upper threshold of bracket, marginal rate)
    brackets = [
        (84120, 0.10),
        (120720, 0.14),
        (193800, 0.20),
        (269280, 0.31),
        (560280, 0.35),
        (float("inf"), 0.47),
    ]

    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if annual_income > prev_limit:
            tax += (min(annual_income, limit) - prev_limit) * rate
        prev_limit = limit

    # Surtax (Mas Yesef): additional 3% on income above 721,560 ₪
    if annual_income > 721560:
        tax += (annual_income - 721560) * 0.03

    return tax


tools = [
    calculate_income_tax
]

SYSTEM_PROMPT = """
You are an expert Israeli Income Tax Agent (Yoez Mas / Roheh Heshbon persona) specializing in Israel's tax ordinance (Pekudat Mas Hachnasa). Your sole purpose is to provide clear, accurate information and calculations regarding Israeli taxation for individuals and businesses.

### ⚠️ CRITICAL MANDATES (STRICT BOUNDARIES)
1. **Domain Restriction:** You must ONLY answer questions directly related to Israeli taxation (e.g., income tax brackets, social security/Bitzuach Leumi, VAT/Ma'am, corporate tax, real estate tax/Mas Shevach, and relevant tax credits/Nekudot Zichuyon). 
   - If a user asks about general accounting, non-Israeli tax systems (like US IRS rules), or unrelated topics, politely refuse by saying: *"I can only assist with questions regarding Israeli taxation laws and regulations."*
2. **Currency Restriction:** You must perform and present ALL calculations and monetary figures exclusively in Israeli New Shekels (ILS / ₪). If a user provides an amount in a foreign currency (e.g., USD, EUR), you must instruct them to convert it to ILS before you can perform the calculation, or assume a mock conversion rate while explicitly stating everything is handled in ILS.
3. **Tool-Only Calculations:** You must call calculate_income_tax when asked about an income tax amount. NEVER compute, estimate, or give a range for income tax yourself. Every income-tax figure in your answer MUST come from a calculate_income_tax tool result. If a tool call returned an error (e.g. "Tool call limit exceeded") or no result for some amount, say explicitly that you cannot calculate the tax for that amount right now, and give NO number for it.

### OPERATIONAL GUIDELINES & PERSONA
- **Tone:** Professional, objective, helpful, and legally cautious.
- **Tax Years:** Always assume the current or most relevant Israeli tax year requested by the user, and explicitly state which tax year's brackets or rules you are applying.
- **Clarity:** Break down complex Israeli tax concepts (like *Madrigot Mas* or *Nekudot Zichuyon*) into easily understandable steps. Use standard Hebrew terms in English transliteration where helpful (e.g., *Mas Hachnasa*, *Bituach Leumi*, *Ma'am*).
- **Disclaimer:** At the end of complex advice or calculations, always include a brief disclaimer stating that your response is for informational purposes only and does not replace official advice from a certified Israeli accountant (CPA) or the Israel Tax Authority (Reshut HaMisim).
"""

@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"{SYSTEM_PROMPT}\n\nToday's date is: {current_date}."


tax_agent = create_agent(
    llm,
    tools,
    system_prompt=SYSTEM_PROMPT,
    middleware=[
        dynamic_system_prompt,
        ToolCallLimitMiddleware(thread_limit=2, run_limit=1, exit_behavior='end')
        ],
    checkpointer=memory
)


def pretty_print_chunk(chunk: dict):
    """Pretty-print a single 'updates' chunk: {node_name: state_update}."""
    for node_name, update in chunk.items():
        print(f"\n{'=' * 30} 🔹 Node: {node_name} {'=' * 30}")
        if not update:
            print("(no state update)")
            continue
        for key, value in update.items():
            if key == "messages":
                for msg in value:
                    msg.pretty_print()
            else:
                print(f"{key}: {value}")


def print_snapshot(snapshot):
    """Print one checkpoint (StateSnapshot) as stored by the checkpointer."""
    cfg = snapshot.config["configurable"]
    meta = snapshot.metadata or {}
    print(f"\n{'#' * 30} 📸 Checkpoint step={meta.get('step')} source={meta.get('source')} {'#' * 30}")
    print(f"checkpoint_id: {cfg.get('checkpoint_id')}")
    parent = snapshot.parent_config["configurable"].get("checkpoint_id") if snapshot.parent_config else None
    print(f"parent_id:     {parent}")
    print(f"created_at:    {snapshot.created_at}")
    print(f"writes:        {meta.get('writes')}")
    print(f"next:          {snapshot.next}")
    print(f"tasks:         {[t.name for t in snapshot.tasks]}")
    for key, value in snapshot.values.items():
        if key == "messages":
            print(f"messages ({len(value)}):")
            for msg in value:
                msg.pretty_print()
        else:
            print(f"{key}: {value}")


def stream(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    seen = {s.config["configurable"]["checkpoint_id"] for s in tax_agent.get_state_history(config)}

    for chunk in tax_agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates"
    ):
        yield chunk

    # Print every checkpoint the checkpointer stored during this run (oldest first)
    new_snapshots = [s for s in tax_agent.get_state_history(config)
                     if s.config["configurable"]["checkpoint_id"] not in seen]
    for snapshot in reversed(new_snapshots):
        print_snapshot(snapshot)



def save_graph_png():
    tax_agent.get_graph().draw_mermaid_png(output_file_path="graph.png")

if __name__ == '__main__':
    save_graph_png()
    # llm.invoke("tell me a joke")