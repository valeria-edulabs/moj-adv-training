from const import EMBEDDING_MODEL
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os


# Load environment variables from .env file
load_dotenv()


def get_db_dir():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(curr_dir, "chroma_db")
    return db_dir

def create_vectorstore():

    print(f"--------- Creating Vectorstore with mortgage data --------")

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define PDF paths and their corresponding bank names
    pdf_files = {
        "hapoalim": os.path.join(curr_dir, "hapoalim_loan_info.pdf"),
        "discount": os.path.join(curr_dir, "discount_loan_info.pdf")
    }

    # INDEXING: LOAD
    print("Loading PDFs and adding metadata...")
    all_docs = []
    for bank_name, file_path in pdf_files.items():
        if os.path.exists(file_path):
            print(f"Loading {bank_name} pdf from {file_path}...")
            loader = PyPDFLoader(file_path=file_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["bank"] = bank_name
            all_docs.extend(docs)
        else:
            print(f"Warning: file {file_path} not found.")

    # INDEXING: SPLIT
    print("Splitting...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )
    all_splits = text_splitter.split_documents(all_docs)
    print(f"Chunks num: {len(all_splits)}")

    # INDEXING: STORE
    print("Creating vector store...")
    db_dir = get_db_dir()
    
    # Remove existing database directory if it exists to ensure a clean database build
    import shutil
    if os.path.exists(db_dir):
        print(f"Clearing old database at {db_dir}...")
        shutil.rmtree(db_dir)

    VECTORSTORE = Chroma.from_documents(
        documents=all_splits,
        embedding=GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL),
        persist_directory=db_dir # Directory where database files will be saved
    )

    print(f"--------- DONE --------")


if __name__ == '__main__':
    create_vectorstore()