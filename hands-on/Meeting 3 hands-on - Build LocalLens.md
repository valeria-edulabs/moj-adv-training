# Hands-On Lab: Build "LocalLens" – A Multimodal Document Search Agent

## 🎯 Objective

Build a privacy-preserving desktop assistant named **LocalLens**. Users can point the agent to a specific folder on their computer (e.g., invoices, design specs, research papers) and ask questions in natural language.

The agent uses **`FilesystemMiddleware`** paired with a multimodal LLM (like Gemini), enabling it to navigate folders, grep text files, and **natively inspect PDFs and images** while strictly confined to the allowed folder.

---

## 🏗️ Architecture & Core Components

1. **`FilesystemBackend(root_dir=..., virtual_mode=True)`**: Sandboxes the agent to the user's chosen root directory and prevents path traversal (e.g., `../../etc/passwd`).  
2. **`FilesystemMiddleware(backend=..., tools=[...])`**: Injects tools into the agent:  
   * `ls` & `glob`: For discovering files and navigating directories.  
   * `grep`: For regex searches across text documents (`.md`, `.txt`, `.json`).  
   * `read_file`: Reads text files and **multimodal binary files (`.pdf`, `.png`, `.jpg`)** by base64-encoding them into native LLM media blocks.  
   * *(Optional)* Exclude `write_file` / `delete` to keep the agent strictly read-only.  
3. **Multimodal LLM (`gemini-flash-lite-latest`)**: Natively reads the PDF documents and images returned by `read_file`.

---

## 📋 Step-by-Step Instructions for Participants

### Step 1: Prepare Sample Documents

Create a sample directory `my_vault/` with a mix of text and multimodal files:

* `invoices/mac_purchase_invoice.pdf` (or an invoice image/text).  
* `design_docs/system_architecture_spec.md` (Markdown doc with architecture notes).  
* `mockups/landing_page_wireframe.png` (a diagram or screenshot).  
* `notes/meeting_notes_2024.txt`.

---

### Step 2: Implement the Agent Backend (`backend.py`)

Implement an agent factory function that takes the user's folder path and returns a sandboxed agent:

```py
from pathlib import Path
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends import FilesystemBackend

SYSTEM_PROMPT = """You are LocalLens, a private desktop document search assistant.
Your job is to help the user find files, inspect specifications, and answer questions based on the allowed directory.

Workflow:
1. Locate relevant files using `glob` (by name/extension) or `grep` (by keyword in text).
2. For specific files (including PDFs and images), use `read_file` to view their contents.
3. Always cite the relative file path and specific details in your final answer.
"""

def create_locallens_agent(folder_path: str):
    abs_folder = str(Path(folder_path).resolve())
    
    # 1. Sandbox backend to the chosen folder
    backend = FilesystemBackend(root_dir=abs_folder, virtual_mode=True)
    
    # 2. Expose search & inspection tools (read-only)
    fs_middleware = FilesystemMiddleware(
        backend=backend,
        tools=["ls", "glob", "grep", "read_file"]
    )
    
    # 3. Initialize multimodal LLM
    llm = init_chat_model("gemini-flash-lite-latest", model_provider="google_genai", temperature=0.1)
    
    # 4. Create agent with middleware
    return create_agent(
        model=llm,
        middleware=[fs_middleware],
        system_prompt=SYSTEM_PROMPT
    )
```

---

### Step 3: Test Core User Scenarios

Have participants run test queries to see how different tools are triggered:

1. **Text Search Scenario:**  
   * **Prompt:** *"Which design documents are in the workspace, and what database is specified?"*  
   * **Expected Agent Action:** Uses `glob("**/*.md")` $\\rightarrow$ finds `system_architecture_spec.md` $\\rightarrow$ calls `read_file` $\\rightarrow$ summarizes the database choice.  
2. **Multimodal PDF / Image Scenario:**  
   * **Prompt:** *"Find the invoice for my Mac and tell me the total amount and purchase date."*  
   * **Expected Agent Action:** Uses `glob("*invoice*")` $\\rightarrow$ finds `mac_purchase_invoice.pdf` $\\rightarrow$ calls `read_file` $\\rightarrow$ Gemini natively reads the PDF and extracts the total and date.  
3. **Security / Boundary Test:**  
   * **Prompt:** *"Can you read `/etc/hosts` or list files in `../../`?"*  
   * **Expected Agent Action:** `FilesystemBackend` blocks access with an error; the agent politely explains that the path is outside the allowed folder.

---

### Step 4: Build the UI / Frontend (Streamlit)

Create an interface in `frontend.py`:

1. **Sidebar:** Text input or file picker for the user to set their **Allowed Directory Path**.  
2. **Chat Window:** Input for user questions with streaming response.  
3. **Tool Call Inspector:** Display an expander showing which tool (`glob`, `grep`, `read_file`) was invoked and what it returned.

---

## 🌟 Bonus / Stretch Challenges

* **PII Redaction:** Add LangChain's `PIIMiddleware` so bank account and credit card numbers found on invoices are automatically redacted from the response.  
* **Smart Summaries:** If a document is over 1,000 lines long, test the eviction threshold (`tool_token_limit_before_evict`) to avoid context window overflow.

