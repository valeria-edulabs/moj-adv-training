# Hands-On Lab: Refactor HyDE Agent into a Retrieval Sub-Agent

## 🎯 1. Exercise Overview

In the previous exercise, you built a single-agent RAG system where the agent directly invoked a HyDE (Hypothetical Document Embeddings) retrieval tool. While effective for simple lookups, a single agent quickly becomes overloaded when managing conversational state, user clarification, multi-step queries, and raw document chunks within a single context window.

In this hands-on lab, participants will refactor the standalone HyDE agent into a **Hierarchical Multi-Agent Architecture (Main Agent + Specialized Retrieval Sub-Agent)**, adopting the sub-agent-as-a-tool pattern demonstrated in `multi_agent/subagent/backend.py`.

### 💡 Why Move to a Sub-Agent Architecture?
1. **Separation of Concerns:** 
   * **Main / Conversational Agent:** Focuses on user empathy, financial intake, clarifying questions, and formatting user-facing advice.
   * **Retrieval Sub-Agent:** A specialized research analyst whose sole job is to formulate hypothetical policy documents, execute vector searches, filter out noise, and return a synthesized factual dossier.
2. **Context Window Hygiene & Isolation:** Raw vector chunks and intermediate hypothetical documents stay inside the sub-agent's execution loop, preventing the main agent's conversational memory from getting polluted.
3. **Multi-Step & Iterative Retrieval:** If a user query requires comparing two loan tracks or needs multiple searches, the sub-agent can execute iterative HyDE lookups autonomously before reporting back to the main agent.

---

## 🏗️ 2. Architecture & Information Flow

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN / SUPERVISOR AGENT                      │
│  - User persona & conversational memory (MemorySaver)           │
│  - Gathers user requirements & resolves conversational context  │
│  - Formulates research requests for the sub-agent               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                 Calls Tool: `call_retrieval_subagent`
                 (Plain English Research Query)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               RETRIEVAL SUB-AGENT (HyDE Specialist)             │
│  - Specialized Document Analyst Persona                         │
│  - Step 1: Generates hypothetical bank policy excerpt (HyDE)    │
│  - Step 2: Queries Chroma Vector Store with hypothetical doc    │
│  - Step 3: Evaluates retrieved chunks & synthesizes factual memo│
└─────────────────────────────────────────────────────────────────┘
                                 │
                 Returns: Structured Factual Dossier
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FINAL USER RESPONSE                        │
│  - Grounded answer synthesized by Main Agent                    │
│  - Standard mandatory financial disclaimer                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 3. Prerequisites & Existing Codebase

Participants will combine and adapt components from:
* **Vector Store & HyDE baseline:** Chroma vector database (`rag_vectors/chroma_db`) and the hypothetical document generator from the previous HyDE lab.
* **Sub-agent Architectural Pattern:** Follow the pattern in `multi_agent/subagent/backend.py`:
  * Sub-agent instantiated with `create_agent`.
  * Sub-agent encapsulated within a `@tool`-decorated function.
  * Main agent instantiated with `create_agent` having the sub-agent tool in its `tools` list.

---

## 📋 4. Step-by-Step Instructions

### Step 1: Define the Retrieval Sub-Agent
* **Tools for Sub-Agent:** Equip the sub-agent with the vector search tool / HyDE retrieval tool built in the previous lab.
* **Sub-Agent Persona (`RETRIEVAL_SUBAGENT_PROMPT`):**
  * Define it as a *Senior Bank Policy & Lending Research Specialist*.
  * Instruct it to analyze incoming research requests, generate hypothetical policy clauses to search the vector database, inspect the retrieved chunks, and return an objective, factual summary citing specific tracks, caps, and indexation rules.
  * Explicitly instruct it: *"Do not converse with the user; communicate purely as an internal technical researcher providing facts to the lead agent."*
* **Creation:**
  ```python
  retrieval_subagent = create_agent(
      model=llm,
      tools=[hyde_retriever_tool],
      system_prompt=RETRIEVAL_SUBAGENT_PROMPT
  )
  ```

---

### Step 2: Wrap the Retrieval Sub-Agent as a Tool
Expose the sub-agent as a callable tool for the main agent using the `@tool` decorator:
* Provide a descriptive docstring explaining to the main agent when and how to call the tool.
* In the tool body, invoke the sub-agent and return the final text response:
  ```python
  @tool("mortgage_research_analyst", description=(
      "Specialized bank policy research sub-agent. Call this tool to look up official "
      "mortgage tracks, interest rate policies, LTV limits, and regulations from Bank Hapoalim. "
      "Pass a clear, descriptive research request in natural language."
  ))
  def call_mortgage_research_analyst(query: str) -> str:
      result = retrieval_subagent.invoke({"messages": [{"role": "user", "content": query}]})
      return result["messages"][-1].content
  ```

---

### Step 3: Implement the Main / Supervisor Agent
* **Persona (`MAIN_SYSTEM_PROMPT`):**
  * An empathetic, knowledgeable Mortgage Advisor for clients in Israel.
  * Directs domain questions to `mortgage_research_analyst`.
  * Responsible for keeping track of user profile details (property price, equity, income, track preferences).
  * Synthesizes technical findings from the analyst into client-friendly advice formatted with markdown tables and bullet points.
  * Appends the mandatory regulatory disclaimer.
* **Checkpointer & Tools:**
  ```python
  main_agent = create_agent(
      model=llm, # or gemini-flash / gemini-pro
      tools=[call_mortgage_research_analyst],
      system_prompt=MAIN_SYSTEM_PROMPT,
      checkpointer=memory
  )
  ```

---

### Step 4: Run & Stream Execution
Update the execution function (`stream`) to run `main_agent.stream(...)` using the `configurable: {"thread_id": ...}` pattern, maintaining persistent multi-turn conversations across user turns.

---

## 🔍 5. Verification & Testing Workflow

| Step | User Query | Expected Sub-Agent & Main Agent Interaction |
| :--- | :--- | :--- |
| **1. Complex Consultation Query** | *"We have 800,000 ILS in savings and want to buy an apartment for 2.4M ILS. What tracks can we take, and what is our financing limit?"* | **Main Agent:** Recognizes that LTV is 66.6% (below the 75% first-home limit). Calls `mortgage_research_analyst` asking for first-home LTV rules and available tracks.<br>**Sub-Agent:** Generates a hypothetical guideline on first-home financing $\rightarrow$ queries Chroma $\rightarrow$ returns factual caps and track limits.<br>**Main Agent:** Delivers a comprehensive financial breakdown to the user. |
| **2. Multi-Part / Comparative Query** | *"Explain the difference between the Prime track and the Fixed Unlinked (Kalatz) track in terms of risk."* | **Main Agent:** Asks the sub-agent to research the regulatory rules and characteristics of both Prime and Fixed Unlinked tracks.<br>**Sub-Agent:** Executes targeted retrieval and returns details on Bank of Israel interest caps and CPI exposure.<br>**Main Agent:** Formats the answer into a clear comparative markdown table. |
| **3. Conversational Context Isolation** | Turn 1: *"Can I get a grace period on repayments?"*<br>Turn 2: *"How long can that period last?"* | Main agent maintains conversational state through `MemorySaver` without re-sending all past raw vector chunks back to the LLM context. Sub-agent is called with a focused query resolving "that period" to mortgage grace periods. |

---

## 💡 Discussion Points for Class Review
1. **Trace Inspection (LangSmith):** Open LangSmith and trace a multi-agent run. Observe how the sub-agent's tool calls and intermediate HyDE generations are nested under the tool call step.
2. **Context Window Savings:** Compare the token consumption of the Main Agent when receiving raw chunks directly vs. receiving the Sub-Agent's distilled summary.
3. **Error Isolation:** If the sub-agent finds no documents, observe how it informs the main agent, allowing the main agent to gracefully ask the user for clarification without hallucinating.
