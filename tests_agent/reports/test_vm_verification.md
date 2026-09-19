# Nightly Test Audit Report: `tax_agent`

**Audit Date:** Nightly Automated Test Verification  
**Target Codebase:** `/Users/valeria/src/trainings/moj-adv-training/tax_agent`  
**Report Destination:** `/Users/valeria/src/trainings/moj-adv-training/tests_agent/reports/test_vm_verification.md`  
**Preferred Test Framework:** `pytest`  
**Audit Focus / Depth:** Comprehensive Audit (Coverage, Quality, Edge Cases)  

---

## 1. Executive Summary

An automated Nightly Test Audit was conducted on the `tax_agent` module located at `/tax_agent` (`backend.py` and `frontend.py`). Currently, the codebase contains **zero unit tests** (`test_*.py` files or test directories). 

While the implementation successfully defines an Israeli Tax AI Agent leveraging LangGraph (`create_agent`), Google Generative AI (`ChatGoogleGenerativeAI`), dynamic system prompts, and a custom income tax calculation tool (`calculate_income_tax`), the total absence of test coverage exposes the system to regressions, incorrect bracket calculations, boundary errors, and fragile agent interactions.

This audit report provides:
1. A rigorous architectural review of `backend.py` and `frontend.py`.
2. Identification of missing tests and coverage gaps.
3. Quality and reliability assessments (including mock strategies for LLMs and deterministic testing for tax brackets).
4. Concrete suggestions for improvement (pytest parametrization, fixture reuse, boundary value testing).
5. An actionable test inventory (**PRESERVE**, **DELETE**, **CREATE**, **EDIT**).

---

## 2. Codebase Architecture & Functionality Review

### A. `backend.py`
- **LLM Initialization:** Configures `ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")`. Depends on environment variables (`GEMINI_API_KEY` / `GOOGLE_API_KEY` via `load_dotenv()`).
- **Memory:** Uses `MemorySaver()` for thread-based persistence across conversations.
- **Tools (`calculate_income_tax`)**:
  - Implements progressive Israeli tax brackets for annual income:
    - Bracket 1: Up to 84,120 ₪ @ 10%
    - Bracket 2: 84,120 ₪ to 120,720 ₪ @ 14%
    - Bracket 3: 120,720 ₪ to 193,800 ₪ @ 20%
    - Bracket 4: 193,800 ₪ to 269,280 ₪ @ 31%
    - Bracket 5: 269,280 ₪ to 560,280 ₪ @ 35%
    - Bracket 6: 560,280 ₪ to 721,560 ₪ @ 47%
    - Above 721,560 ₪: 50% base rate + an additional 3% surtax on income exceeding 721,560 ₪.
- **System Prompt & Dynamic Prompting:**
  - Enforces strict domain boundaries (Israeli taxation only, Hebrew/English transliteration terms like *Mas Hachnasa*, *Bituach Leumi*, *Ma'am*).
  - Enforces currency restrictions (exclusively Israeli New Shekels / ILS / ₪).
  - Uses `@dynamic_prompt` to inject `datetime.now().strftime("%Y-%m-%d")` into model requests.
- **Agent Construction:** Built using `create_agent(llm, tools, middleware=[dynamic_system_prompt], checkpointer=memory)`.
- **Streaming & Graph Generation:** Provides `stream(text, thread_id)` yielding chunk updates, and `save_graph_png()` to export Mermaid graph diagrams.

### B. `frontend.py`
- Streamlit web interface for conversational interaction with the tax agent.
- Manages session state history by thread ID (`st.session_state.history_by_thread`).
- Renders user prompts, tool calls (`tool_call`), tool responses (`tool_response`), and assistant responses.

---

## 3. Test Coverage & Quality Gaps

### A. Missing Test Coverage
1. **Core Business Logic (`calculate_income_tax`):**
   - No tests verifying tax calculations across bracket boundaries (e.g., exactly at 84,120 ₪, 120,720 ₪, 721,560 ₪).
   - No tests for negative income, zero income, extremely high incomes, or invalid types (strings, `None`).
2. **Middleware & Dynamic Prompting (`dynamic_system_prompt`):**
   - No test verifying that `datetime.now()` is correctly appended to the prompt template.
3. **Agent Behavior & Tool Execution:**
   - No unit or integration tests verifying that `tax_agent` correctly invokes `calculate_income_tax` when queried about income tax amounts.
   - No mock testing for `ChatGoogleGenerativeAI` responses (preventing expensive API calls and network flakiness during CI/CD).
4. **Streaming Generator:**
   - No test verifying that `stream(text, thread_id)` yields expected chunk formats.
5. **Frontend State & Rendering:**
   - No Streamlit component tests (e.g., using `streamlit.testing.v1.AppTest`) to verify session state initialization, thread switching, and message history rendering.

### B. Test Quality & Reliability Risks
- **Over-reliance on Live LLM Calls:** If tests were written against live Gemini API endpoints, they would suffer from non-determinism, rate limits, latency, and monetary costs. Mocks or recorded cassettes (e.g., `pytest-mock` or `responses`) are mandatory.
- **Numerical Precision:** Floating-point arithmetic in Python (`float`) can introduce rounding errors when calculating tax brackets (e.g., `0.1 + 0.2 != 0.3`). Tests should use `pytest.approx()` for monetary assertions.

---

## 4. Concrete Suggestions for Improvement

1. **Unit Test Isolation for `calculate_income_tax`:**
   - Implement `pytest.mark.parametrize` covering zero, intra-bracket, bracket-boundary, and high-income surtax scenarios.
2. **Deterministic Agent Testing via Mocking:**
   - Mock `ChatGoogleGenerativeAI` or LangGraph execution using `unittest.mock` to verify that user queries correctly trigger tool calls and parse responses without hitting external APIs.
3. **Streamlit UI Testing:**
   - Introduce `AppTest` from `streamlit.testing.v1` to validate sidebar configuration, thread switching, and history clearing.
4. **CI/CD Integration:**
   - Place unit tests under `tests/` directory so pytest runs automatically in nightly pipelines.

---

## 5. Actionable Inventory

### Tests to PRESERVE
*None currently exist.* (0 files).

### Tests to DELETE
*None currently exist.* (0 files).

### Tests to CREATE

| Test Name | Target Function / Module | Scenario | Expected Assertion |
| :--- | :--- | :--- | :--- |
| `test_calculate_income_tax_zero` | `calculate_income_tax` | Income = `0.0` | Returns `0.0` |
| `test_calculate_income_tax_bracket_1` | `calculate_income_tax` | Income = `84120.0` (exact bracket 1 limit) | Returns `84120 * 0.10` (`8412.0`) within `pytest.approx` |
| `test_calculate_income_tax_bracket_2` | `calculate_income_tax` | Income = `100000.0` (spanning brackets 1 & 2) | Returns correct cumulative tax within `pytest.approx` |
| `test_calculate_income_tax_high_surtax` | `calculate_income_tax` | Income = `800000.0` (exceeding 721,560 ₪ surtax threshold) | Returns correct base tax + 50% + 3% surtax within `pytest.approx` |
| `test_calculate_income_tax_negative` | `calculate_income_tax` | Income = `-5000.0` (edge case / invalid input) | Handles gracefully or returns `0.0` (depending on policy) |
| `test_dynamic_system_prompt` | `dynamic_system_prompt` | Passes mock `ModelRequest` | Returns string containing system prompt and current date formatted as `YYYY-MM-DD` |
| `test_agent_stream_mocked` | `stream` (in `backend.py`) | Mocks `tax_agent.stream` execution | Yields expected chunk dictionary structures for a given user query and thread ID |
| `test_streamlit_app_smoke` | `frontend.py` (Streamlit UI) | Loads `frontend.py` via `AppTest` | Verifies title `"Israeli Tax AI Agent"` renders successfully and default thread ID exists |

### Tests to EDIT
*None currently exist.* (All suggested tests are new creations).

---

## 6. Conclusion
Implementing the tests detailed in the Actionable Inventory will elevate the test coverage of `tax_agent` from **0%** to a robust, maintainable standard, ensuring calculation accuracy and stable agent behavior across nightly runs.
