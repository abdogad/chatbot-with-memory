import streamlit as st
import requests
import os

# Page config
st.set_page_config(
    page_title="Chatbot with Memory",
    page_icon="🤖",
    layout="wide"
)

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
    import uuid
    st.session_state.user_id = str(uuid.uuid4())
if 'use_memory' not in st.session_state:
    st.session_state.use_memory = True

# App title
st.title("🤖 Chatbot with Memory")
st.caption("This chatbot remembers your previous conversations and can use that context to provide better responses.")

# Sidebar
with st.sidebar:
    st.header("Settings")
    st.session_state.use_memory = st.toggle("Enable Memory", value=st.session_state.use_memory)
    
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        # Here you would also want to clear the backend memory
        try:
            response = requests.post(
                f"{st.session_state.get('backend_url', 'http://localhost:8000')}/clear_memories",
                json={"user_id": st.session_state.user_id}
            )
            if response.status_code == 200:
                st.success("Conversation history cleared!")
            else:
                st.error("Failed to clear conversation history")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
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

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Call backend API
            backend_url = st.session_state.get('backend_url', 'http://localhost:8000')
            response = requests.post(
                f"{backend_url}/chat",
                json={
                    "user_id": st.session_state.user_id,
                    "message": prompt,
                    "use_memory": st.session_state.use_memory
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                full_response = data["response"]
                used_memory = data.get("used_memory", False)
                relevant_memories = data.get("relevant_memories", [])
                
                # Display response
                message_placeholder.markdown(full_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "used_memory": used_memory,
                    "relevant_memories": relevant_memories
                })
                
                # Show memory indicator if memory was used
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
