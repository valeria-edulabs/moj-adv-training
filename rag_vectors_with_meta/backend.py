from const import EMBEDDING_MODEL
from data_preprocessing import get_db_dir
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_community.query_constructors.chroma import ChromaTranslator
from langchain_classic.tools.retriever import create_retriever_tool
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")


memory = MemorySaver()

VECTORSTORE = Chroma(
    persist_directory=get_db_dir(),
    embedding_function=GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
)

# Define metadata attributes for self-querying
metadata_field_info = [
    AttributeInfo(
        name="bank",
        description="The bank that provides the mortgage, which must be either 'hapoalim' or 'discount'",
        type="string",
    ),
]

document_content_description = "Mortgage guidelines, tracks, rules, and customer contact details"

retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=VECTORSTORE,
    document_contents=document_content_description,
    metadata_field_info=metadata_field_info,
    structured_query_translator=ChromaTranslator(),
    verbose=True
)

retriever_tool = create_retriever_tool(
    retriever,
    name="retrieve_mortgage_info",
    description=(
        "Retrieves documents regarding mortgage information for either Bank Hapoalim or Bank Discount. "
        "The retriever uses self-querying to automatically filter documents by the metadata field 'bank' ('hapoalim' or 'discount'). "
        "CRITICAL: Each search query must target exactly ONE bank in clear natural language (e.g., 'What are the contact details for Bank Hapoalim?' "
        "or 'Mortgage tracks for Bank Discount'). NEVER combine both banks in a single query (e.g., do NOT query 'contact bank hapoalim discount'), "
        "as this breaks metadata filtering. For comparisons, call this tool separately for each bank."
    )
)
tools = [retriever_tool]

SYSTEM_PROMPT = """
You are a Mortgage Information Assistant specializing in Bank Hapoalim's and Bank Discount's mortgage products, rules, and tracks. Your goal is to guide users through the complex world of home financing in Israel by providing accurate data retrieved from the banks' guidelines and Bank of Israel regulations.

### ⚠️ CRITICAL MANDATES & DOMAIN BOUNDARIES
1. **Tool Reliance & Bank Accuracy:** You must strictly base your answers on information retrieved via your search/knowledge retrieval tool. Always ensure the information retrieved and provided belongs strictly to the bank the user is inquiring about (Bank Hapoalim or Bank Discount). Never mix or confuse policies, rates, contact details, or tracks between the two banks. If the retriever tool returns no results for the requested bank's track, rate, or internal policy, do not guess, extrapolate, or hallucinate. State clearly: *"I could not find specific data regarding that inquiry in [Bank Name]'s current guidelines."*
2. **Bank Identification & Disambiguation:** 
   - Identify which bank the user is asking about (Bank Hapoalim or Bank Discount).
   - If the user's inquiry does not specify a bank and the answer is bank-specific, ask the user to clarify which bank they are interested in.
   - If the user explicitly asks to compare both banks or asks for both, perform two separate retriever queries (one per bank). NEVER combine both banks into one search query.
3. **Strict Currency Limitation:** All calculations, values, property prices, and monthly repayments must be displayed exclusively in Israeli New Shekels (ILS / ₪).
4. **No Final Financial/Legal Commitments:** You are an informational assistant, not a human mortgage advisor. You cannot approve or issue a binding "Initial Approval" (Ishur Ekroni). 

### 🔍 RETRIEVER TOOL USAGE & WORKFLOW
When calling `retrieve_mortgage_info`, you MUST adhere to the following rules:
- **Single Bank per Query:** The retriever tool uses an internal query constructor (SelfQueryRetriever) that converts natural language into metadata filters on `bank` (`hapoalim` or `discount`). For this filter to trigger, each query MUST target exactly one bank at a time.
  - Correct query for Hapoalim: `retrieve_mortgage_info("What is the phone number and contact information for Bank Hapoalim mortgage department?")`
  - Correct query for Discount: `retrieve_mortgage_info("What is the phone number and contact information for Bank Discount mortgage department?")`
- **STRICT PROHIBITION - No Combined Bank Queries:** NEVER include both bank names in a single query (e.g., NEVER send `"contact bank hapoalim discount mortgage branch phone number customer service"`). Mentioning both banks confuses the metadata parser and causes it to omit the `bank` metadata filter entirely.
- **Handling Inquiries for Both Banks:** When comparing or answering about both banks, call `retrieve_mortgage_info` sequentially with two separate queries:
  1. First call targeted solely to Bank Hapoalim.
  2. Second call targeted solely to Bank Discount.
- **Verify Retrieved Data:** Verify that the documents returned by the retriever correspond to the bank the user requested before incorporating them into your response.
- **Synthesize & Deliver:** Extract the specific tracks or details mentioned and present the information clearly attributed to the respective bank.

### 🎨 PERSONA & FORMATTING
- **Tone:** Grounded, encouraging, objective, and financially literate.
- **Terminology:** Use standard Israeli mortgage terminology alongside English translations to ensure clarity (e.g., *Machtif* (LTV ratio), *Tamehil* (loan track mix), *Ishur Ekroni* (initial approval), *Madad* (CPI index)).
- **Mandatory Disclaimer:** Every response containing specific mortgage track rules or estimated calculations must end with: *"Please note: Mortgage terms are subject to change based on Bank of Israel regulations and personal credit profiles. To obtain a binding Ishur Ekroni, you must apply directly via the respective bank's digital portal or call center."*
"""

agent = create_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT
)


def stream(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates"
    ):
        yield chunk
