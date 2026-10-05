import streamlit as st
import sys
import os

# Adjust path to import backend correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from custom_workflow.backend import stream, get_state, clear_state

st.set_page_config(
    page_title="Form Fill & Return Resolution Chat",
    layout="wide"
)

# Title & Subtitle
st.title("🔄 Interactive Custom Return Flow")
st.markdown(
    "Demonstrating combining **Deterministic Nodes** (Python Validator, mock database refund logic, mock escalation ticketing) "
    "with **Agentic Nodes** (LLM-driven personalized proposals, natural language agreement classification)."
)
st.markdown("---")

# Setup history state by thread ID
if "history_by_thread" not in st.session_state:
    st.session_state.history_by_thread = {}

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Configuration")
    thread_id = st.text_input("Active Thread ID", value="return_session_2")
    
    st.markdown("---")
    st.subheader("💡 Workflow Architecture")
    st.markdown(
        """
        **1. Validator (Deterministic Python)**
        Checks the user messages for 6-digit Order IDs and keywords (damage, wrong size, incorrect item).
        
        **2. Proposer (Agentic LLM)**
        Generates a personalized solution matching the customer's exact issue and asks if they accept it.
        
        **3. Intent Classifier (Agentic LLM)**
        Understands natural language agreement (e.g. "Sure, that works!" vs "No, I want human help").
        
        **4. Refund / Escalation (Deterministic Python)**
        Mocks final API actions (credits refund or schedules manual support review).
        """
    )
    st.markdown("---")
    if st.button("🔄 Reset / Clear Session"):
        clear_state(thread_id)
        st.session_state.history_by_thread[thread_id] = []
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()

# Retrieve or create history for this thread
if thread_id not in st.session_state.history_by_thread:
    st.session_state.history_by_thread[thread_id] = []

messages = st.session_state.history_by_thread[thread_id]

# Fetch current State from backend to populate inspector
state = get_state(thread_id)
order_id = state.get("order_id")
return_reason = state.get("return_reason")
proposal = state.get("proposal")
flow_stage = state.get("flow_stage", "collecting_info")
customer_decision = state.get("customer_decision")
resolution_message = state.get("resolution_message")

# Layout: Split into Chat and Inspector panels
col_chat, col_state = st.columns([5, 3], gap="large")

with col_state:
    st.subheader("📋 Live State Inspector")
    
    # Progress Calculation
    progress_val = 0
    if order_id: progress_val += 25
    if return_reason: progress_val += 25
    if flow_stage == "proposed": progress_val = 75
    elif flow_stage == "resolved": progress_val = 100
    
    # Displays state cards
    with st.container(border=True):
        st.markdown("### **Form Slots Status**")
        
        # Order ID card
        if order_id:
            st.markdown(f"🟢 **Order ID:** `{order_id}`")
        else:
            st.markdown("🔴 **Order ID:** *Missing (6-digit number)*")
            
        # Return Reason card
        if return_reason:
            st.markdown(f"🟢 **Reason:** `{return_reason}`")
        else:
            st.markdown("🔴 **Reason:** *Missing (Damaged / Size / Wrong Item)*")
            
        # Customer Decision card
        if customer_decision:
            if customer_decision == "accepted":
                st.markdown("🟢 **Customer Decision:** `Accepted proposal`")
            else:
                st.markdown("🔴 **Customer Decision:** `Rejected proposal (Escalate)`")
        else:
            st.markdown("⚪ **Customer Decision:** *Pending Proposed Solution*")
            
        st.markdown("**Flow Completion**")
        st.progress(progress_val)
    
    # Diagram showing current execution stage
    with st.container(border=True):
        st.markdown("### **Active Pipeline Steps**")
        
        # Determine step states
        step1 = "⚪ Pending"
        step2 = "⚪ Pending"
        step3 = "⚪ Pending"
        step4 = "⚪ Pending"
        
        if flow_stage == "collecting_info":
            if not (order_id and return_reason):
                step1 = "🔵 Active (Collecting details)"
            else:
                step1 = "✅ Done"
                step2 = "🔵 Active (Generating proposal)"
        elif flow_stage == "proposed":
            step1 = "✅ Done"
            step2 = "✅ Done"
            if not customer_decision:
                step3 = "🔵 Active (Waiting for user confirmation)"
            else:
                step3 = "✅ Done"
                step4 = "🔵 Active (Processing transaction)"
        elif flow_stage == "resolved":
            step1 = "✅ Done"
            step2 = "✅ Done"
            step3 = "✅ Done"
            step4 = "✅ Done"
            
        st.markdown(f"**1. Validator (Deterministic):** {step1}")
        st.markdown(f"**2. Proposer (LLM):** {step2}")
        st.markdown(f"**3. Classifier (LLM):** {step3}")
        st.markdown(f"**4. Resolution (Deterministic):** {step4}")
        
        st.caption(
            "Flow: Collect Info ➔ Propose Solution ➔ Classify Answer ➔ Refund or Escalate"
        )

with col_chat:
    st.subheader("💬 Support Chat")
    
    # Initialize message list if empty
    if not messages:
        messages.append({
            "role": "assistant",
            "content": "Welcome! To process your return, please provide your 6-digit Order ID and tell us why you are returning the item.",
            "type": "instruction"
        })
        st.session_state.history_by_thread[thread_id] = messages
        
    # Render chat history
    for msg in messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                msg_type = msg.get("type", "instruction")
                if msg_type == "proposal":
                    st.markdown("### 💡 Proposed Solution")
                    st.info(msg["content"])
                elif msg_type == "resolution":
                    if "Approved" in msg["content"]:
                        st.success(msg["content"])
                    else:
                        st.warning(msg["content"])
                else:
                    st.markdown(msg["content"])

    # Reusable turn handler for both chat inputs and selectbox selections
    def handle_turn(display_text: str, stream_input: str):
        messages.append({"role": "user", "content": display_text})
        st.session_state.history_by_thread[thread_id] = messages
        
        with st.chat_message("assistant"):
            status_container = st.container()
            message_placeholder = st.empty()
            
            full_response = ""
            msg_type = "instruction"
            
            # Stream execution
            for chunk in stream(stream_input, thread_id):
                # 1. Validator Node
                if "deterministic_validator" in chunk:
                    val_data = chunk["deterministic_validator"]
                    if val_data:
                        with status_container:
                            with st.status("⚙️ Executing Deterministic Validator Node", state="complete") as status:
                                st.write(f"- Scanned input: *\"{stream_input}\"*")
                                st.write(f"- Extracted Order ID: `{val_data.get('order_id')}`")
                                st.write(f"- Extracted Return Reason: `{val_data.get('return_reason')}`")
                        
                        if not (val_data.get("order_id") and val_data.get("return_reason")) or val_data.get("system_instruction") == "Your return request has already been resolved. Please reset the chat or start a new thread if you have another query.":
                            full_response = val_data["system_instruction"]
                            message_placeholder.markdown(full_response)
                
                # 2. Proposer Node
                if "agentic_proposer" in chunk:
                    prop_data = chunk["agentic_proposer"]
                    if prop_data:
                        with status_container:
                            with st.status("🤖 Executing Agentic Proposer Node", state="complete") as status:
                                st.write("- Slots validated successfully!")
                                st.write("- Calling LLM to draft proposed solution...")
                        
                        msg_type = "proposal"
                        full_response = prop_data["proposal"]
                        message_placeholder.markdown("### 💡 Proposed Solution")
                        message_placeholder.info(full_response)
                    
                # 3. Decision Classifier Node
                if "agentic_decision_handler" in chunk:
                    decision_data = chunk["agentic_decision_handler"]
                    if decision_data:
                        with status_container:
                            with st.status("🤖 Executing Intent Classifier Node", state="complete") as status:
                                st.write(f"- Classifying customer response: *\"{stream_input}\"*")
                                st.write(f"- Evaluated Intent Decision: **{decision_data.get('customer_decision')}**")
                
                # 4. Refund Node
                if "deterministic_refund" in chunk:
                    refund_data = chunk["deterministic_refund"]
                    if refund_data:
                        with status_container:
                            with st.status("⚙️ Processing Refund Transaction", state="complete") as status:
                                st.write("- Executing mock database query to authorize refund credit...")
                        
                        msg_type = "resolution"
                        full_response = refund_data["resolution_message"]
                        message_placeholder.success(full_response)
                
                # 5. Escalate Node
                if "deterministic_escalate" in chunk:
                    escalate_data = chunk["deterministic_escalate"]
                    if escalate_data:
                        with status_container:
                            with st.status("⚙️ Escalating Support Case", state="complete") as status:
                                st.write("- Opening CRM support ticket...")
                                st.write("- Scheduling staff notification...")
                        
                        msg_type = "resolution"
                        full_response = escalate_data["resolution_message"]
                        message_placeholder.warning(full_response)
            
            if full_response:
                messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "type": msg_type
                })
                st.session_state.history_by_thread[thread_id] = messages
                
                # Refresh to update the live inspector details immediately
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()

    # Render interactive dropdown if Order ID is known but Reason is missing
    if order_id and not return_reason and flow_stage == "collecting_info":
        with st.container(border=True):
            st.markdown("📋 **Please select your return reason:**")
            selected_option = st.selectbox(
                "Return Reason Options",
                ["-- Select Reason --", "Damaged Item", "Incorrect Size", "Wrong Item Shipped", "Other"],
                label_visibility="collapsed"
            )
            submit_reason = st.button("Confirm & Submit Reason")
            if submit_reason and selected_option != "-- Select Reason --":
                user_text = ""
                if selected_option == "Damaged Item":
                    user_text = "damaged"
                elif selected_option == "Incorrect Size":
                    user_text = "incorrect size"
                elif selected_option == "Wrong Item Shipped":
                    user_text = "wrong item"
                else:
                    user_text = "other"
                
                handle_turn(f"Reason: {selected_option}", user_text)

    # User chat input
    # Determine custom placeholder depending on flow stage
    input_placeholder = "E.g., I want to return my order #123456 because it was damaged"
    if flow_stage == "proposed":
        input_placeholder = "E.g., Yes, please process the refund"
    elif flow_stage == "resolved":
        input_placeholder = "This session has been resolved. Press Reset in sidebar to start a new chat."
        
    if prompt := st.chat_input(input_placeholder, disabled=(flow_stage == "resolved")):
        with st.chat_message("user"):
            st.markdown(prompt)
        handle_turn(prompt, prompt)
