import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="Chatbot with Memory",
    page_icon="🤖",
    layout="wide"
)

# --- New: Single-message lock ---
if 'message_pending' not in st.session_state:
    st.session_state.message_pending = False
if 'pending_prompt' not in st.session_state:
    st.session_state.pending_prompt = None

# Authentication check
if not st.user.is_logged_in:
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# Initialize session state with backend URL from secrets
if 'backend_url' not in st.session_state:
    st.session_state.backend_url = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# Custom CSS
st.markdown("""
<style>
    .stTextInput > div > div > input {
        padding: 10px;
    }
    .stButton button {
        width: 100%;
        padding: 10px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .chat-message {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        max-width: 80%;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    .memory-indicator {
        font-size: 0.8em;
        color: #666;
        margin-top: 5px;
    }
    .memory-badge {
        background-color: #e8f5e9;
        border-left: 3px solid #4CAF50;
        padding: 8px;
        margin: 5px 0;
        border-radius: 0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = st.user.email
if 'use_memory' not in st.session_state:
    st.session_state.use_memory = True

# App title
st.title("🤖 Chatbot with Memory")
st.caption("This chatbot remembers your previous conversations and can use that context to provide better responses.")

# Sidebar
with st.sidebar:
    st.header("Settings")
    st.markdown(f"Logged in as: {st.user.email}")
    st.session_state.use_memory = st.toggle("Enable Memory", value=st.session_state.use_memory)
    
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        try:
            response = requests.post(
                f"{st.session_state.backend_url}/clear_memories",
                json={"user_id": st.session_state.user_id}
            )
            if response.status_code == 200:
                st.success("Conversation history cleared!")
            else:
                st.error("Failed to clear conversation history")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    if st.button("Log out"):
        st.logout()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This is a chatbot with memory capabilities. It can remember previous conversations 
    and use that context to provide better responses.
    """)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("used_memory") and len(message.get("relevant_memories", [])) > 0:
            with st.expander("🔍 Used memory context"):
                for memory in message["relevant_memories"]:
                    st.markdown(f'<div class="memory-badge">{memory}</div>', unsafe_allow_html=True)

# New: disable chat input while waiting for a reply
user_input = st.chat_input("Type your message here...", disabled=st.session_state.message_pending)

# New: queue the prompt and trigger rerun
if user_input and not st.session_state.message_pending:
    st.session_state.pending_prompt = user_input
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.message_pending = True
    st.rerun()

# New: if waiting on a prompt, handle the assistant response
if st.session_state.message_pending and st.session_state.pending_prompt:
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            response = requests.post(
                f"{st.session_state.backend_url}/chat",
                json={
                    "user_id": st.session_state.user_id,
                    "message": st.session_state.pending_prompt,
                    "use_memory": st.session_state.use_memory
                }
            )
            if response.status_code == 200:
                data = response.json()
                full_response = data["response"]
                used_memory = data.get("used_memory", False)
                relevant_memories = data.get("relevant_memories", [])
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "used_memory": used_memory,
                    "relevant_memories": relevant_memories
                })
                if used_memory and relevant_memories:
                    with st.expander("🔍 Used memory context"):
                        for memory in relevant_memories:
                            st.markdown(f'<div class="memory-badge">{memory}</div>', unsafe_allow_html=True)
            else:
                error_msg = "Sorry, I encountered an error processing your request."
                message_placeholder.markdown(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "error": True
                })
        except Exception as e:
            error_msg = f"Error connecting to the server: {str(e)}"
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "error": True
            })
    # Reset pending state and rerun
    st.session_state.pending_prompt = None
    st.session_state.message_pending = False
    st.rerun()
