from rag_vectors.const import EMBEDDING_MODEL
from data_preprocessing import get_db_dir
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



VECTORSTORE = Chroma(
    persist_directory=get_db_dir(),
    embedding_function=GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
)

retriever = VECTORSTORE.as_retriever(search_kwargs={"k": 3})
response = retriever.invoke("How can i contact the bank?")
print(response)