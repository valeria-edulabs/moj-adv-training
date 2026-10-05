from data_preprocessing import get_db_dir
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


VECTORSTORE = Chroma(
    persist_directory=get_db_dir(),
    embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
)

# Test retrieving Hapoalim information
print("--- Querying with bank: hapoalim filter ---")
hapoalim_retriever = VECTORSTORE.as_retriever(
    search_kwargs={
        "k": 2,
        "filter": {"bank": "hapoalim"}
    }
)
hapoalim_response = hapoalim_retriever.invoke("What are the contact details?")
for doc in hapoalim_response:
    print(f"Metadata: {doc.metadata}")
    print(f"Content: {doc.page_content}...\n")

# Test retrieving Discount information
print("--- Querying with bank: discount filter ---")
discount_retriever = VECTORSTORE.as_retriever(
    search_kwargs={
        "k": 2,
        "filter": {"bank": "discount"}
    }
)
discount_response = discount_retriever.invoke("What are the contact details?")
for doc in discount_response:
    print(f"Metadata: {doc.metadata}")
    print(f"Content: {doc.page_content}...\n")