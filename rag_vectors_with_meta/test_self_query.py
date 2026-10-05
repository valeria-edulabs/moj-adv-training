from data_preprocessing import get_db_dir
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from dotenv import load_dotenv

load_dotenv()

# Initialize embeddings and LLM
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)

# Initialize vector store
VECTORSTORE = Chroma(
    persist_directory=get_db_dir(),
    embedding_function=embeddings
)

# Define the metadata field info
metadata_field_info = [
    AttributeInfo(
        name="bank",
        description="The bank that provides the mortgage, which must be either 'hapoalim' or 'discount'",
        type="string",
    ),
]

document_content_description = "Mortgage guidelines, tracks, rules, and customer contact details"

from langchain_community.query_constructors.chroma import ChromaTranslator

# Create the SelfQueryRetriever
retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=VECTORSTORE,
    document_contents=document_content_description,
    metadata_field_info=metadata_field_info,
    structured_query_translator=ChromaTranslator(),
    verbose=True
)

# Run test queries
if __name__ == "__main__":
    # Test 1: Query that should filter for Bank Hapoalim
    print("--- Test 1: Query for Hapoalim contact details ---")
    docs_hapoalim = retriever.invoke("What are the contact details for Hapoalim bank?")
    for doc in docs_hapoalim:
        print(f"Bank: {doc.metadata.get('bank')} | Page: {doc.metadata.get('page')}")
        print(f"Content snippet: {doc.page_content[:150]}...\n")

    # Test 2: Query that should filter for Bank Discount
    print("--- Test 2: Query for Discount mortgage rules ---")
    docs_discount = retriever.invoke("Show me the interest rates or steps for discount bank")
    for doc in docs_discount:
        print(f"Bank: {doc.metadata.get('bank')} | Page: {doc.metadata.get('page')}")
        print(f"Content snippet: {doc.page_content[:150]}...\n")
