import os
import sys
import uuid
import pandas as pd
import streamlit as st

# Adjust path to import backend correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data_analysis_sandbox.backend import (
        get_sandbox_status,
        reset_thread,
        resume_stream,
        stream,
    )
except ImportError:
    from backend import (
        get_sandbox_status,
        reset_thread,
        resume_stream,
        stream,
    )


def render_artifact(artifact, key: str | None = None):
    """Render rich visual artifacts (Plotly chart or DataFrame table) produced inside the sandbox."""
    if artifact is not None and isinstance(artifact, dict):
        art_type = artifact.get("type")
        art_data = artifact.get("data")
        try:
            if art_type == "dataframe" and art_data is not None:
                st.success("✨ Rich DataFrame artifact rendered from Docker Sandbox")
                df_artifact = pd.DataFrame(art_data)
                st.dataframe(df_artifact, use_container_width=True)
            elif art_type == "plotly" and art_data is not None:
                st.success("📊 Interactive Plotly visualization loaded from Docker Sandbox")
                chart_key = key if key is not None else f"plotly_{uuid.uuid4().hex}"
                st.plotly_chart(art_data, use_container_width=True, key=chart_key)
            elif "exit_code" in artifact:
                code = artifact.get("exit_code")
                if code == 0:
                    st.caption("✅ Container command completed successfully (Exit Code: 0). No visual artifact generated.")
                else:
                    st.warning(f"⚠️ Container command finished with exit code {code}.")
            elif art_type:
                st.warning(f"Unknown artifact type: {art_type}")
            else:
                st.info("No visual artifact (chart or dataframe) generated for this tool run.")
        except Exception as e:
            st.error(f"Error rendering sandbox artifact ({art_type}): {str(e)}")
    else:
        st.info("No visual artifact generated for this tool run.")


st.set_page_config(
    page_title="Data Analysis Agent — Docker Sandbox",
    page_icon="🐳",
    layout="wide",
)

# Custom styling for rich dark aesthetics
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Glassmorphic card styling */
.metric-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.25rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.metric-card:hover {
    transform: translateY(-2px);
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(56, 189, 248, 0.3);
}

.main-title {
    background: linear-gradient(to right, #0284c7, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.6rem;
    margin-bottom: 0.2rem;
    text-align: center;
}

.subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    text-align: center;
    margin-bottom: 1.5rem;
}

.hero-banner {
    background: linear-gradient(90deg, rgba(2, 132, 199, 0.08) 0%, rgba(129, 140, 248, 0.08) 100%);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 18px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(10px);
}

.sandbox-badge {
    display: inline-block;
    background: rgba(14, 165, 233, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.stStatus {
    background-color: rgba(15, 23, 42, 0.7) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div style="text-align:center;"><span class="sandbox-badge">🐳 DEEPAGENTS DOCKER SANDBOX</span></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">📦 Data Analysis with Isolated Docker Sandbox</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Secure, Containerized Code Execution with Human-in-the-Loop Verification</p>', unsafe_allow_html=True)

# Load dataset to display stats at the top
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products_stock_data.csv")
if os.path.exists(csv_path):
    df_stats = pd.read_csv(csv_path)
    total_products = len(df_stats)
    total_stock = df_stats['qty in stock'].sum()
    avg_price = df_stats['price'].mean()
else:
    total_products, total_stock, avg_price = 0, 0, 0.0

# Header Stats Banner
with st.container():
    st.markdown('<div class="hero-banner">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.9rem; margin:0; font-weight:600;">Total Products</p><h3 style="color:#38bdf8; margin:0; font-size:1.8rem; font-weight:800;">{total_products}</h3></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.9rem; margin:0; font-weight:600;">Total Stock Volume</p><h3 style="color:#818cf8; margin:0; font-size:1.8rem; font-weight:800;">{total_stock:,}</h3></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.9rem; margin:0; font-weight:600;">Average Unit Price</p><h3 style="color:#34d399; margin:0; font-size:1.8rem; font-weight:800;">${avg_price:.2f}</h3></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Session state initialization
if "history_by_thread" not in st.session_state:
    st.session_state.history_by_thread = {}

if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Sandbox Configuration")
    thread_id = st.text_input("Active Session / Thread ID", value="docker_session_1")

    status = get_sandbox_status(thread_id)
    st.markdown("### 🐳 Docker Container Status")
    if status["active"]:
        st.success(f"**Container**: `{status['container_name']}`")
        st.caption(f"**Sandbox ID**: `{status['sandbox_id']}`")
        st.caption(f"**Network**: `{status['network']}`")
        st.caption(f"**Memory Limit**: `{status['memory']}`")
    else:
        st.info("Container will automatically start when the first command is executed.")

    st.markdown("---")
    st.markdown("### 📋 Sample Questions")
    st.info(
        "💡 **Try asking:**\n\n"
        "1. *What is the average price of the products?*\n"
        "2. *Show me a pie chart with product in stock per category*\n"
        "3. *Show me a table of Electronics with quantity less than 50*"
    )

    st.markdown("---")
    if st.button("🧹 Reset Container & Thread", use_container_width=True):
        reset_thread(thread_id)
        st.session_state.history_by_thread[thread_id] = []
        st.session_state.pending_interrupt = None
        st.success(f"Container for {thread_id} stopped and cleaned up.")
        st.rerun()

# Retrieve or create history for this thread
if thread_id not in st.session_state.history_by_thread:
    st.session_state.history_by_thread[thread_id] = []

messages = st.session_state.history_by_thread[thread_id]


def handle_stream(stream_generator, messages, thread_id):
    """Handle streamed events from the agent with Docker sandbox backend."""
    full_response = ""
    text_placeholder = st.empty()

    for chunk in stream_generator:
        # 1. Handle Human-In-The-Loop Interrupts
        if "__interrupt__" in chunk:
            interrupt_obj = chunk["__interrupt__"][0]
            st.session_state.pending_interrupt = {
                "value": interrupt_obj.value,
                "id": interrupt_obj.id,
            }
            st.rerun()

        # 2. Handle Tools Node Updates
        if "tools" in chunk:
            tool_msg = chunk["tools"]["messages"][0]
            artifact = getattr(tool_msg, "artifact", None)
            stream_key = f"stream_{thread_id}_{len(messages)}_{uuid.uuid4().hex[:8]}"

            with st.container():
                st.write("🔄 **Docker Sandbox Execution Result:**")
                if artifact is not None:
                    tab_user, tab_model = st.tabs(["🎨 User View (Rendered Artifact)", "🤖 Model View (Docker stdout/stderr)"])
                    with tab_user:
                        render_artifact(artifact, key=f"{stream_key}_user")
                    with tab_model:
                        st.info("Raw output from inside Docker container sent to the LLM:")
                        st.code(tool_msg.content, language="text")
                else:
                    tab_model, tab_user = st.tabs(["🤖 Model View (Docker stdout/stderr)", "🎨 User View (Rendered Artifact)"])
                    with tab_model:
                        st.info("Raw output from inside Docker container sent to the LLM:")
                        st.code(tool_msg.content, language="text")
                    with tab_user:
                        render_artifact(artifact, key=f"{stream_key}_user")

            messages.append({
                "role": "tool_response",
                "content": tool_msg.content,
                "artifact": artifact,
            })
            st.session_state.history_by_thread[thread_id] = messages
            continue

        # 3. Handle Agent Nodes Yielding Messages
        for node_name, node_update in chunk.items():
            if isinstance(node_update, dict) and "messages" in node_update:
                for msg in node_update["messages"]:
                    # Tool Calls
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            with st.status(f"🛠️ Sandbox Call: `{tc['name']}`", state="running") as stat:
                                st.write("Arguments passed to container:")
                                st.json(tc["args"])
                                stat.update(label=f"🛠️ Sandbox Call: `{tc['name']}`", state="complete")

                            messages.append({
                                "role": "tool_call",
                                "name": tc["name"],
                                "args": tc["args"],
                            })
                            st.session_state.history_by_thread[thread_id] = messages

                    # Model Content / Explanations
                    if getattr(msg, "content", None):
                        text_content = ""
                        if isinstance(msg.content, str):
                            text_content = msg.content
                        elif isinstance(msg.content, list):
                            for part in msg.content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    text_content += part.get("text", "")
                                elif isinstance(part, str):
                                    text_content += part

                        if text_content:
                            full_response += text_content
                            text_placeholder.markdown(full_response)

    if full_response:
        messages.append({"role": "assistant", "content": full_response})
        st.session_state.history_by_thread[thread_id] = messages


# Render chat history
for idx, msg in enumerate(messages):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])

    elif msg["role"] == "tool_call":
        with st.status(f"🛠️ Sandbox Call: `{msg['name']}`", state="complete"):
            st.write("Arguments passed to container:")
            st.json(msg["args"])

    elif msg["role"] == "tool_response":
        with st.container():
            st.write("🔄 **Docker Sandbox Execution Result:**")
            artifact = msg.get("artifact")
            hist_key = f"hist_{thread_id}_{idx}"
            if artifact is not None:
                tab_user, tab_model = st.tabs(["🎨 User View (Rendered Artifact)", "🤖 Model View (Docker stdout/stderr)"])
                with tab_user:
                    render_artifact(artifact, key=f"{hist_key}_user")
                with tab_model:
                    st.info("Raw output from inside Docker container sent to the LLM:")
                    st.code(msg["content"], language="text")
            else:
                tab_model, tab_user = st.tabs(["🤖 Model View (Docker stdout/stderr)", "🎨 User View (Rendered Artifact)"])
                with tab_model:
                    st.info("Raw output from inside Docker container sent to the LLM:")
                    st.code(msg["content"], language="text")
                with tab_user:
                    render_artifact(artifact, key=f"{hist_key}_user")

    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])


# Human-In-The-Loop Approval UI
if st.session_state.pending_interrupt:
    interrupt_info = st.session_state.pending_interrupt
    value = interrupt_info["value"]
    action_req = value["action_requests"][0]
    action_name = action_req.get("name", "execute")
    action_args = action_req.get("args", {})
    original_command = action_args.get("command", "")

    st.markdown("---")
    st.markdown(
        '<div class="metric-card" style="border: 2px solid #0284c7; background: rgba(2, 132, 199, 0.05);">',
        unsafe_allow_html=True,
    )
    st.warning("⚠️ **Human-in-the-Loop: Docker Sandbox Execution Approval Required**")
    st.markdown("The agent is requesting to execute the following command inside the isolated Docker container:")
    st.code(original_command, language="bash")

    st.markdown("##### ✏️ Review & Edit Command:")
    edited_command = st.text_area("You can modify the command before it runs inside the container:", value=original_command, height=140)

    col_app, col_rej, col_edit = st.columns(3)
    with col_app:
        if st.button("✅ Approve & Run in Docker", use_container_width=True):
            decision = {"decisions": [{"type": "approve"}]}
            st.session_state.pending_interrupt = None
            st.info("Executing approved command in Docker sandbox...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()

    with col_rej:
        if st.button("❌ Reject Execution", use_container_width=True):
            decision = {"decisions": [{"type": "reject", "message": "User denied command execution."}]}
            st.session_state.pending_interrupt = None
            st.info("Rejecting command execution...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()

    with col_edit:
        if st.button("⚡ Run Edited Command", use_container_width=True):
            decision = {
                "decisions": [{
                    "type": "edit",
                    "edited_action": {
                        "name": action_name,
                        "args": {"command": edited_command},
                    },
                }],
            }
            st.session_state.pending_interrupt = None
            st.info("Executing modified command in Docker sandbox...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# Chat input box
if prompt := st.chat_input("Ask a question about the products stock data..."):
    if st.session_state.pending_interrupt:
        st.error("Please resolve the pending Docker execution approval above first.")
    else:
        with st.chat_message("user"):
            st.markdown(prompt)

        messages.append({"role": "user", "content": prompt})
        st.session_state.history_by_thread[thread_id] = messages

        with st.chat_message("assistant"):
            handle_stream(stream(prompt, thread_id), messages, thread_id)
