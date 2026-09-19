import os
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

# Adjust path to import backend correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(current_dir)
if workspace_root not in sys.path:
    sys.path.append(workspace_root)

from tests_agent.backend import run_test_audit, list_saved_reports

st.set_page_config(
    page_title="Nightly Test Audit - Tests Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Dashboard
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e9ecef;
    }
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-blue { background-color: #e3f2fd; color: #0d47a1; }
    .badge-green { background-color: #e8f5e9; color: #1b5e20; }
    .badge-purple { background-color: #f3e5f5; color: #4a148c; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "last_report_content" not in st.session_state:
    st.session_state.last_report_content = None
if "last_report_path" not in st.session_state:
    st.session_state.last_report_path = None
if "last_summary" not in st.session_state:
    st.session_state.last_summary = None
if "last_tool_logs" not in st.session_state:
    st.session_state.last_tool_logs = []
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# Sidebar: Job History & Info
with st.sidebar:
    st.image("https://img.icons8.com/color/96/test-tube.png", width=64)
    st.title("Audit History")
    st.caption("Saved Nightly Reports on Filesystem")

    saved_reports = list_saved_reports()
    if saved_reports:
        st.write(f"**Found {len(saved_reports)} report(s):**")
        for rep in saved_reports:
            with st.expander(f"📄 {rep['filename']}", expanded=False):
                st.caption(f"📅 {rep['modified']} | 💾 {rep['size_kb']} KB")
                if st.button("Load Report", key=f"btn_{rep['filename']}"):
                    with open(rep["path"], "r", encoding="utf-8") as f:
                        st.session_state.last_report_content = f.read()
                    st.session_state.last_report_path = rep["path"]
                    st.session_state.last_summary = "Loaded from existing filesystem report."
                    st.session_state.last_tool_logs = []
                    st.rerun()
    else:
        st.info("No prior reports found in `tests_agent/reports/`.")

    st.markdown("---")
    st.subheader("ℹ️ Architecture")
    st.markdown("""
    - **Engine**: LangChain `create_agent`
    - **Model**: `gemini-flash-lite-latest` via `init_chat_model`
    - **Middleware**: `FilesystemMiddleware`
    - **Tools**: `ls`, `read_file`, `glob`, `grep`, `write_file`
    """)

    st.markdown("---")
    st.subheader("Quick Presets")
    if st.button("🎯 Use Dummy Demo Project", type="primary"):
        st.session_state["preset_code_dir"] = os.path.join(current_dir, "dummy_project", "src")
        st.session_state["preset_tests_dir"] = os.path.join(current_dir, "dummy_project", "tests")
        st.rerun()

    if st.button("Use Tax Agent as Target"):
        st.session_state["preset_code_dir"] = os.path.join(workspace_root, "tax_agent")
        st.session_state["preset_tests_dir"] = ""
        st.rerun()

# Main Header
st.markdown('<div class="main-header">🧪 Nightly Test Audit Job Configuration</div>', unsafe_allow_html=True)
st.markdown("""
<div class="sub-header">
    Configure and trigger an automated agent job to audit Python code and unit tests.
    Powered by <b>LangChain Filesystem Middleware</b> and <b>Google Gemini</b>.
</div>
""", unsafe_allow_html=True)

# Default path calculations
default_code_dir = st.session_state.get(
    "preset_code_dir",
    os.path.join(current_dir, "dummy_project", "src")
)
default_tests_dir = st.session_state.get(
    "preset_tests_dir",
    os.path.join(current_dir, "dummy_project", "tests")
)
timestamp_default = datetime.now().strftime("%Y%m%d_%H%M%S")
default_report_path = os.path.join(current_dir, "reports", f"test_audit_report_{timestamp_default}.md")

# Job Configuration Form
with st.container():
    st.subheader("1. Job Target Configuration")
    
    col_code, col_tests = st.columns(2)
    with col_code:
        code_dir_input = st.text_input(
            "Target Code Repository / Directory *",
            value=default_code_dir,
            help="Absolute path to the Python source code directory to be audited."
        )
        # Validation badge
        if os.path.exists(code_dir_input):
            st.caption("✅ Path exists on local filesystem")
        else:
            st.caption("⚠️ Directory does not exist yet")

    with col_tests:
        tests_dir_input = st.text_input(
            "Existing Unit Tests Directory (Optional)",
            value=default_tests_dir,
            placeholder="e.g. /path/to/tests (Leave empty if inside code repo)",
            help="Optional separate directory containing unit tests. If blank, agent searches inside the code directory."
        )
        if tests_dir_input and os.path.exists(tests_dir_input):
            st.caption("✅ Path exists on local filesystem")
        elif tests_dir_input:
            st.caption("⚠️ Tests directory not found")

    st.subheader("2. Nightly Execution Settings")
    col_rep, col_fw, col_focus = st.columns([2, 1, 1.5])
    
    with col_rep:
        report_path_input = st.text_input(
            "Output Report Destination File *",
            value=default_report_path,
            help="Filesystem path where the Markdown audit report will be stored by the agent."
        )
    
    with col_fw:
        framework_input = st.selectbox(
            "Preferred Test Framework",
            ["pytest", "unittest"],
            index=0
        )
    
    with col_focus:
        focus_input = st.selectbox(
            "Audit Focus & Depth",
            [
                "Comprehensive Audit (Coverage, Quality, Edge Cases)",
                "Quality & Anti-Patterns (Mocking, Fixtures, Flakiness)",
                "Fast Inventory (Missing Tests & Action Items Only)",
                "Regression & Boundary Focus"
            ],
            index=0
        )

    additional_notes = st.text_area(
        "Custom Audit Directives (Optional)",
        placeholder="e.g., Focus on error handling in edge brackets, check whether API calls are mocked appropriately, etc.",
        height=70
    )

st.markdown("---")

# Run Button
run_col, _, _ = st.columns([1.5, 2, 2])
with run_col:
    start_audit = st.button("🚀 Run Nightly Test Audit Job", type="primary", use_container_width=True)

# Execution Logic
if start_audit:
    if not os.path.exists(code_dir_input):
        st.error(f"Cannot start audit: Target code directory does not exist: `{code_dir_input}`")
    else:
        st.session_state.is_running = True
        st.session_state.last_tool_logs = []
        
        job_options = {
            "test_framework": framework_input,
            "audit_focus": focus_input,
            "notes": additional_notes
        }

        # Progress tracking container
        status_box = st.status("🔍 Initializing Test Audit Agent with Filesystem Middleware...", expanded=True)
        live_log_placeholder = st.empty()
        
        tool_logs = []
        full_text = ""

        try:
            for event in run_test_audit(
                code_dir=code_dir_input,
                tests_dir=tests_dir_input,
                report_path=report_path_input,
                job_options=job_options
            ):
                event_type = event.get("type")
                
                if event_type == "status":
                    status_box.write(f"ℹ️ {event['message']}")
                
                elif event_type == "tool_call":
                    tool_name = event["name"]
                    args = event["args"]
                    tool_logs.append({"type": "call", "name": tool_name, "args": args, "time": datetime.now().strftime("%H:%M:%S")})
                    status_box.write(f"🛠️ **Tool Call**: `{tool_name}` with args: `{args}`")
                
                elif event_type == "tool_response":
                    content = str(event["content"])
                    preview = content[:200] + ("..." if len(content) > 200 else "")
                    tool_logs.append({"type": "response", "content": preview, "time": datetime.now().strftime("%H:%M:%S")})
                    status_box.write(f"📥 **Tool Result**: {preview}")
                
                elif event_type == "content":
                    full_text = event.get("full", "")
                
                elif event_type == "complete":
                    st.session_state.last_report_content = event["report_content"]
                    st.session_state.last_report_path = event["report_path"]
                    st.session_state.last_summary = event["summary"]
                    st.session_state.last_tool_logs = tool_logs
                    status_box.update(label="✅ Test Audit Job Completed Successfully!", state="complete", expanded=False)
                    st.success(f"Audit report saved to filesystem: `{event['report_path']}`")
                
                elif event_type == "error":
                    status_box.update(label="❌ Error during audit", state="error")
                    st.error(event["message"])
                    break

        except Exception as err:
            status_box.update(label="❌ Exception encountered", state="error")
            st.error(f"Unexpected error: {str(err)}")
        finally:
            st.session_state.is_running = False

# Results Presentation Area
if st.session_state.last_report_content:
    st.markdown("---")
    st.subheader("📊 Audit Report & Findings")

    # Metrics summary header
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Report Status", "Saved to Disk ✅")
    with m_col2:
        report_size_kb = round(len(st.session_state.last_report_content.encode("utf-8")) / 1024, 2)
        st.metric("Report File Size", f"{report_size_kb} KB")
    with m_col3:
        st.metric("Location", os.path.basename(st.session_state.last_report_path or "report.md"))

    st.caption(f"📁 Absolute Path: `{st.session_state.last_report_path}`")

    # Download Button
    st.download_button(
        label="💾 Download Markdown Report",
        data=st.session_state.last_report_content,
        file_name=os.path.basename(st.session_state.last_report_path or "audit_report.md"),
        mime="text/markdown"
    )

    # Tabs for different report views
    tab_report, tab_raw, tab_tools = st.tabs(["📄 Formatted Report", "📝 Raw Markdown", "🛠️ Execution Trace"])

    with tab_report:
        st.markdown(st.session_state.last_report_content)

    with tab_raw:
        st.code(st.session_state.last_report_content, language="markdown")

    with tab_tools:
        st.write("**Agent Tool Call Trace:**")
        if st.session_state.last_tool_logs:
            for log in st.session_state.last_tool_logs:
                if log["type"] == "call":
                    st.markdown(f"**[{log['time']}] 🛠️ `{log['name']}`**")
                    st.json(log["args"])
                else:
                    st.markdown(f"**[{log['time']}] 📥 Output:**")
                    st.code(log["content"])
        else:
            st.info("No tool call trace stored for this report.")
