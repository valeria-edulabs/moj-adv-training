# **🎯 System Health Agent with Prebuilt Middleware & HITL**

## **1\. Exercise Overview**

In this exercise, participants will upgrade their stateful **System Health & Diagnostic Agent** by refactoring soft system prompt guardrails into deterministic code-level middleware integrated into LangChain's create\_agent construct. The updated agent performs operational health checks (system performance metrics, endpoint status checks, and directory metadata inspections), enforces strict security controls, and persists long-lived conversational state to a MongoDB database across application restarts.  
Participants will configure two essential production middleware patterns:

> * **Human-in-the-Loop (HITL) Middleware:** To gate file-system access by intercepting inspect\_directory\_metadata so execution halts and requires explicit developer authorization before local directory structures are inspected.  
> * **Summarization Middleware:** To manage long-running diagnostic sessions by automatically condensing chat history when message limits are reached, preserving vital context while staying within token budgets.

### **Example Decision Workflow (HITL Interrupt):**

User: "Check host metrics, then inspect directory metadata for ./src."  
Agent: \[Executes get\_system\_metrics automatically\]  
Agent: \[Intercepts inspect\_directory\_metadata call\]  
System: ⚠️ INTERRUPT: 'inspect\_directory\_metadata' requires human approval.  
        Target Path: ./src  
        Action Options: \[Approve, Edit, Reject\]

User Response: "Approve"  
Agent: Executing inspect\_directory\_metadata... Directory ./src contains 14 files and 3 subdirectories (total size: 1.2MB).

## **2\. Prerequisites & Setup**

Participants will extend their existing system-health-agent project directory built during previous tasks.

### **Stack & SDK Choice:**

> * **Python:** Install langchain-core, langchain-google-genai, langgraph, langgraph-checkpoint-mongodb, and pymongo. Ensure middleware modules are imported (e.g., from langchain.middleware import HumanInTheLoopMiddleware, SummarizationMiddleware).  
> * **Node.js / TypeScript:** Install @langchain/core, @langchain/google-genai, @langchain/langgraph, and @langchain/langgraph-checkpoint-mongodb. Import humanInTheLoopMiddleware and summarizationMiddleware.

### **LLM API Key & Infrastructure Configuration:**

> * **API Key:** Ensure GOOGLE\_API\_KEY is set in your .env file.  
> * **Persistence (MongoDB Checkpointer):** Continued use of MongoDBSaver (HITL **requires** state persistence to support state pauses and handle Command(resume=...) execution loops).

## **3\. Core Requirements & Tasks**

### **Task 1: Native Diagnostic Tools**

Maintain the standard read-only tool suite established in the baseline architecture:

| Tool Name | Functionality | Security Constraint   |
| :---- | :---- | :---- |
| get\_system\_metrics | Gathers real-time host performance metrics (CPU usage %, memory consumption/available, and disk space details). | Read-Only / Unrestricted Execution |
| check\_endpoint\_health | Accepts a target URL string, sends an HTTP GET request, and reports status code, latency (ms), and response headers. | Read-Only / Unrestricted Execution |
| inspect\_directory\_metadata | Accepts a local folder path string (dir\_path) and returns structural metadata (total size, file count, extension breakdown). | Strict HITL Approval Required |

### **Task 2: Middlewares & Agent Creation**

Instantiate the agent using create\_agent and pass the middleware configurations:

> * **Human-in-the-Loop (HITL) Middleware:**  
  * Read-only diagnostic metrics (get\_system\_metrics) and network health evaluations (check\_endpoint\_health) must run **automatically** without triggering interrupts.  
  * inspect\_directory\_metadata must trigger an immediate \_\_interrupt\_\_ requesting explicit human authorization prior to inspecting local file paths.  
  * Supported approval actions: approve, edit (e.g., modifying target ./src to ./src/utils), and reject.  
> * **Summarization Middleware:**  
  * Configure a trigger threshold to automatically summarize chat history once context reaches or exceeds 6 messages.  
  * Ensure historical execution metrics and context are condensed without losing active session state.  
> * **System Persona:** Enforce an Infrastructure Health Specialist persona with step-by-step diagnostic reasoning.

### **Task 3: Database Checkpointer & Harness Integration**

> * Connect MongoDBSaver to local MongoDB or MongoDB Atlas using a dedicated database (agent\_health\_db) and checkpoint collection.  
> * Update the execution harness (Interactive CLI or Streamlit UI) to inspect returned stream state for \_\_interrupt\_\_ signals.  
> * When an interrupt occurs on inspect\_directory\_metadata, prompt the operator for terminal input to handle approval via Command(resume=...).

## **4\. The 4-Step Verification Workflow**

| Step | Action / Prompt | Objective / Expected Result   |
| :---- | :---- | :---- |
| **1\. Unrestricted Diagnostics** | "Check system metrics and evaluate https://httpbin.org/status/200." | get\_system\_metrics and check\_endpoint\_health run automatically in sequence with direct output. No HITL prompt is raised. |
| **2\. HITL Interception** | "Inspect metadata for path ./src." | Agent halts execution right before executing inspect\_directory\_metadata, returning an \_\_interrupt\_\_ payload to the harness. |
| **3\. Decision & State Resume** | Operator inputs **Approve** (or edits path to ./src/components). | Agent resumes from state via Command(resume=...), executes the tool with authorized parameters, and returns directory details. |
| **4\. Summarization Trigger** | Perform 4 additional diagnostic prompt turns. | SummarizationMiddleware automatically condenses older context into a summary block while maintaining active session context. |

