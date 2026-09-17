from datetime import datetime
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")


memory = MemorySaver()

@tool
def calculate_income_tax(annual_income: float):
    """Calculate annual income tax based on annual income"""
    tax = 0
    brackets = [
        (84120, 0.10),
        (120720, 0.14),
        (193800, 0.20),
        (269280, 0.31),
        (560280, 0.35),
        (721560, 0.47),
    ]

    remaining_income = annual_income

    for i, (limit, rate) in enumerate(brackets):
        if remaining_income > limit:
            tax += limit * rate
            remaining_income -= limit
        else:
            tax += remaining_income * rate
            return tax

    # Additional tax for incomes above 721,560 ₪
    tax += remaining_income * 0.50
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
    middleware=[dynamic_system_prompt],
    checkpointer=memory
)


def stream(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk in tax_agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates"
    ):
        yield chunk



def save_graph_png():
    tax_agent.get_graph().draw_mermaid_png(output_file_path="graph.png")

if __name__ == '__main__':
    save_graph_png()
    # llm.invoke("tell me a joke")