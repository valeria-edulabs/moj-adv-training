import streamlit as st
import sys
import os
import uuid
import pandas as pd
import plotly.graph_objects as go

# Adjust path to import backend correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from advanced_data_analysis.backend import stream, resume_stream

def render_artifact(artifact, key: str | None = None):
    if artifact is not None and isinstance(artifact, dict):
        art_type = artifact.get("type")
        art_data = artifact.get("data")
        st.success(f"Rich artifact loaded (Type: {art_type.upper()})")
        if art_type == "dataframe":
            df_artifact = pd.DataFrame(art_data)
            st.dataframe(df_artifact, use_container_width=True)
        elif art_type == "plotly":
            chart_key = key if key is not None else f"plotly_{uuid.uuid4().hex}"
            st.plotly_chart(art_data, use_container_width=True, key=chart_key)
        else:
            st.warning(f"Unknown artifact type: {art_type}")
    else:
        st.warning("No artifact generated for this tool run.")

st.set_page_config(
    page_title="Advanced Data Analyst with HITL",
    layout="wide"
)

# Custom premium CSS
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
    padding: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.metric-card:hover {
    transform: translateY(-3px);
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
}

.main-title {
    background: linear-gradient(to right, #38bdf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.8rem;
    margin-bottom: 0.2rem;
    text-align: center;
}

.subtitle {
    font-size: 1.1rem;
    color: #94a3b8;
    text-align: center;
    margin-bottom: 2rem;
}

.hero-banner {
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.05) 0%, rgba(192, 132, 252, 0.05) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    backdrop-filter: blur(10px);
}

/* Status container improvements */
.stStatus {
    background-color: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* Tabs customization */
div[data-baseweb="tab-list"] {
    background-color: transparent !important;
}

div[data-baseweb="tab"] {
    font-weight: 600 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📦 Advanced Data Analysis (Human-in-the-Loop)</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Review, Confirm, or Modify proposed Python code before execution</p>', unsafe_allow_html=True)

# Load dataset to display stats at the top
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products_stock_data.csv")
df_stats = pd.read_csv(csv_path)
total_products = len(df_stats)
total_stock = df_stats['qty in stock'].sum()
avg_price = df_stats['price'].mean()

# Header Stats
with st.container():
    st.markdown('<div class="hero-banner">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.95rem; margin:0; font-weight:600;">Total Products</p><h3 style="color:#38bdf8; margin:0; font-size:2rem; font-weight:800;">{total_products}</h3></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.95rem; margin:0; font-weight:600;">Total Stock Volume</p><h3 style="color:#c084fc; margin:0; font-size:2rem; font-weight:800;">{total_stock:,}</h3></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><p style="color:#94a3b8; font-size:0.95rem; margin:0; font-weight:600;">Average Unit Price</p><h3 style="color:#34d399; margin:0; font-size:2rem; font-weight:800;">${avg_price:.2f}</h3></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Setup state variables
if "history_by_thread" not in st.session_state:
    st.session_state.history_by_thread = {}

if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Configuration")
    thread_id = st.text_input("Active Thread ID", value="hitl_analysis_session_1")
    
    st.markdown("---")
    st.markdown("### 📋 Sample Questions")
    st.info("💡 **Try asking:**\n\n1. *What is the average price of the products?*\n2. *Show me a pie chart with product in stock per category*\n3. *Show me a table of Electronics with quantity less than 50*")
    
    st.markdown("---")
    if st.button("Clear Thread History", use_container_width=True):
        st.session_state.history_by_thread[thread_id] = []
        st.session_state.pending_interrupt = None
        st.rerun()

# Retrieve or create history for this thread
if thread_id not in st.session_state.history_by_thread:
    st.session_state.history_by_thread[thread_id] = []

messages = st.session_state.history_by_thread[thread_id]

# Helper to handle stream outputs and rendering
def handle_stream(stream_generator, messages, thread_id):
    full_response = ""
    text_placeholder = st.empty()
    
    for chunk in stream_generator:
        # Handle LangGraph interrupts
        if "__interrupt__" in chunk:
            interrupt_obj = chunk["__interrupt__"][0]
            st.session_state.pending_interrupt = {
                "value": interrupt_obj.value,
                "id": interrupt_obj.id
            }
            # Rerun script to render the approval form
            st.rerun()

        # Handle tools node updates
        if "tools" in chunk:
            tool_msg = chunk["tools"]["messages"][0]
            artifact = getattr(tool_msg, "artifact", None)
            stream_key = f"stream_{thread_id}_{len(messages)}_{uuid.uuid4().hex[:8]}"
            
            with st.container():
                st.write("🔄 **Tool Execution Result:**")
                if artifact is not None:
                    tab_user, tab_model = st.tabs(["🎨 What the User Sees (Artifact)", "🤖 What the Model Sees (Content)"])
                    with tab_user:
                        render_artifact(artifact, key=f"{stream_key}_user")
                    with tab_model:
                        st.info("This raw text is sent back to the LLM to guide its next response.")
                        st.code(tool_msg.content, language="text")
                else:
                    tab_model, tab_user = st.tabs(["🤖 What the Model Sees (Content)", "🎨 What the User Sees (Artifact)"])
                    with tab_model:
                        st.info("This raw text is sent back to the LLM to guide its next response.")
                        st.code(tool_msg.content, language="text")
                    with tab_user:
                        render_artifact(artifact, key=f"{stream_key}_user")
            
            messages.append({
                "role": "tool_response",
                "content": tool_msg.content,
                "artifact": artifact
            })
            st.session_state.history_by_thread[thread_id] = messages
            continue

        # Handle agent nodes yielding messages
        for node_name, node_update in chunk.items():
            if isinstance(node_update, dict) and "messages" in node_update:
                for msg in node_update["messages"]:
                    # Handle Tool Calls
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            with st.status(f"🛠️ Tool Call: {tc['name']}", state="running") as status:
                                st.write("Parameters:")
                                st.json(tc["args"])
                                status.update(label=f"🛠️ Tool Call: {tc['name']}", state="complete")
                            
                            messages.append({
                                "role": "tool_call",
                                "name": tc["name"],
                                "args": tc["args"]
                            })
                            st.session_state.history_by_thread[thread_id] = messages
                            
                    # Handle Assistant text response
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

    # Save assistant text content
    if full_response:
        messages.append({"role": "assistant", "content": full_response})
        st.session_state.history_by_thread[thread_id] = messages

# Render chat history
for idx, msg in enumerate(messages):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
            
    elif msg["role"] == "tool_call":
        with st.status(f"🛠️ Tool Call: {msg['name']}", state="complete"):
            st.write("Parameters:")
            st.json(msg["args"])
            
    elif msg["role"] == "tool_response":
        with st.container():
            st.write("🔄 **Tool Execution Result:**")
            artifact = msg.get("artifact")
            hist_key = f"hist_{thread_id}_{idx}"
            if artifact is not None:
                tab_user, tab_model = st.tabs(["🎨 What the User Sees (Artifact)", "🤖 What the Model Sees (Content)"])
                with tab_user:
                    render_artifact(artifact, key=f"{hist_key}_user")
                with tab_model:
                    st.info("This raw text is sent back to the LLM to guide its next response.")
                    st.code(msg["content"], language="text")
            else:
                tab_model, tab_user = st.tabs(["🤖 What the Model Sees (Content)", "🎨 What the User Sees (Artifact)"])
                with tab_model:
                    st.info("This raw text is sent back to the LLM to guide its next response.")
                    st.code(msg["content"], language="text")
                with tab_user:
                    render_artifact(artifact, key=f"{hist_key}_user")
                    
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])

# Render pending interrupt if exists (approval UI)
if st.session_state.pending_interrupt:
    interrupt_info = st.session_state.pending_interrupt
    value = interrupt_info["value"]
    action_req = value["action_requests"][0]
    original_code = action_req["args"].get("code", "")
    
    st.markdown("---")
    st.markdown('<div class="metric-card" style="border: 2px solid #f59e0b; background: rgba(245, 158, 11, 0.02);">', unsafe_allow_html=True)
    st.warning("⚠️ **Human-in-the-Loop: Code Execution Approval Required**")
    st.markdown("The agent is proposing to execute the following Python code to analyze the dataset:")
    st.code(original_code, language="python")
    
    # Editing Area
    st.markdown("##### ✏️ Review & Edit Code:")
    edited_code = st.text_area("You can modify the code below before running it:", value=original_code, height=180)
    
    # Action buttons
    col_app, col_rej, col_edit = st.columns(3)
    with col_app:
        if st.button("✅ Approve & Run Original", use_container_width=True):
            decision = {"decisions": [{"type": "approve"}]}
            st.session_state.pending_interrupt = None
            st.info("Executing approved code...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()
            
    with col_rej:
        if st.button("❌ Reject / Deny Execution", use_container_width=True):
            decision = {"decisions": [{"type": "reject", "message": "User rejected the code execution."}]}
            st.session_state.pending_interrupt = None
            st.info("Rejecting code execution...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()
            
    with col_edit:
        if st.button("⚡ Run Updated Code", use_container_width=True):
            decision = {
                "decisions": [{
                    "type": "edit",
                    "edited_action": {
                        "name": "python_interpreter",
                        "args": {"code": edited_code}
                    }
                }]
            }
            st.session_state.pending_interrupt = None
            st.info("Executing updated code...")
            with st.chat_message("assistant"):
                handle_stream(resume_stream(decision, thread_id), messages, thread_id)
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

# User prompt input
if prompt := st.chat_input("Ask a question about the products stock data..."):
    if st.session_state.pending_interrupt:
        st.error("Please resolve the pending code execution approval above first.")
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Store user message
        messages.append({"role": "user", "content": prompt})
        st.session_state.history_by_thread[thread_id] = messages
        
        # Generate response
        with st.chat_message("assistant"):
            handle_stream(stream(prompt, thread_id), messages, thread_id)
