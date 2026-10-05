# Hands-On Lab: Implement an Agent with HyDE (Hypothetical Document Embeddings)

## 🎯 1. Exercise Overview

In standard Retrieval-Augmented Generation (RAG), a user's question (short, colloquial, interrogative) is embedded directly to search for matching chunks in a vector database (which are long, formal, declarative passages). This discrepancy is known as the **query-to-document semantic gap**, which often leads to sub-optimal retrieval when search keywords or grammatical structures diverge.

**Hypothetical Document Embeddings (HyDE)** addresses this challenge through a two-step retrieval paradigm:
1. **Hypothetical Generation:** An LLM generates a hypothetical, ideal document/passage that answers the user's inquiry, mimicking the style, terminology, and structure of real documents.
2. **Dense Document-to-Document Search:** The vector database embeds and searches against the *hypothetical document* rather than the raw query.
3. **Agent Synthesis:** The agent evaluates the retrieved *ground-truth* documents from the database to formulate the verified final response.

```
┌────────────┐       ┌────────────────────────┐       ┌─────────────────────────┐
│ User Query │ ───►  │  Hypothetical Document │ ───►  │   Chroma Vector Store   │
│            │       │ Generator (Gemini LLM) │       │ (Document Similarity)   │
└────────────┘       └────────────────────────┘       └────────────┬────────────┘
                                                                   │
                                                                   ▼
┌────────────┐       ┌────────────────────────┐       ┌─────────────────────────┐
│  Grounded  │ ◄───  │    LangChain Agent     │ ◄───  │ Retrieved Authentic     │
│   Answer   │       │     (create_agent)     │       │ Knowledge Chunks        │
└────────────┘       └────────────────────────┘       └─────────────────────────┘
```

---

## 🛠️ 2. Prerequisites & Setup

Participants will build on top of the mortgage RAG components located in `rag_vectors/`:

* **Vector Store & Embeddings:** Chroma vector database populated from `hapoalim_loan_info.pdf` via `rag_vectors/data_preprocessing.py`, utilizing `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")`.
* **LLM:** `ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")`.
* **Agent Framework:** `langchain.agents.create_agent` with LangGraph `MemorySaver`.
* **Environment:** Ensure `GOOGLE_API_KEY` is defined in `.env`.

---

## 📋 3. Step-by-Step Tasks

### Task 1: Reusing the Baseline Vector Store
* Load the persisted Chroma vector store from `rag_vectors/chroma_db` using `GoogleGenerativeAIEmbeddings`.
* Confirm baseline retriever functionality: `retriever = vectorstore.as_retriever(search_kwargs={"k": 3})`.

### Task 2: Build the Hypothetical Document Generator
Create a focused prompt and LLM invocation chain that accepts a natural language query and generates a synthetic, authoritative policy passage:
* **Input:** User query (e.g., *"Can I get a mortgage if I buy a second apartment?"*).
* **Prompt Instructions:** Ask the model to generate a formal excerpt from official bank lending guidelines answering the query. Instruct it not to output conversation starters, greetings, or disclaimers—only raw document text.
* **Output:** A clean string containing the hypothetical passage.

### Task 3: Implement the HyDE Retrieval Mechanism
Construct a retrieval function or custom retriever that replaces the raw query embedding with the hypothetical document embedding:
1. Receive the incoming query.
2. Invoke the generator from Task 2 to produce the hypothetical document text.
3. Query the Chroma vector store using `vectorstore.similarity_search(hypothetical_doc, k=3)`.
4. Return the resulting ground-truth documents.

### Task 4: Expose HyDE as an Agent Tool & Instantiate the Agent
* Wrap the HyDE retrieval logic into a LangChain tool (using `@tool` or `Tool.from_function`).
* Provide clear tool metadata (`name="retrieve_mortgage_info_hyde"` and a concise description describing when the agent should call it).
* Register the tool with `create_agent` alongside a system prompt instructing the agent to:
  * Rely strictly on the retrieved ground-truth documents.
  * Ignore any fabricated or hallucinatory figures in intermediate hypothetical generations.
  * Provide answers grounded in Israeli mortgage regulations (ILS currency, official tracks).

---

## 🔍 4. Verification & Testing Workflow

| Test Scenario | Query / Prompt | Expected Behavior |
| :--- | :--- | :--- |
| **1. Terminology Gap Test** | *"My apartment is now worth much more than when I bought it, how can I lower my monthly bill?"* | **Standard Retrieval:** Struggles because the query does not mention banking terms.<br>**HyDE Retrieval:** LLM generates a passage discussing *refinancing (Michzur)* and *loan-to-value (LTV / Machtif) adjustments*, pulling the exact relevant mortgage clauses from the PDF. |
| **2. Conversational Slang Test** | *"What's the deal with taking money based on the Prime rate?"* | HyDE transforms the informal query into a structured paragraph describing the *Ribit Prime* track, its indexation rules, and Bank of Israel variable-rate caps. |
| **3. Grounded Agent Response** | End-to-end question answering via CLI or Streamlit UI. | The agent invokes the HyDE retriever tool, retrieves the actual guidelines from the database, and formulates an accurate, grounded reply with the mandatory disclaimer. |
