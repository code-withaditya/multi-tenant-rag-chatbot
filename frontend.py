import streamlit as st
import requests
import uuid
import json

# 🌐 BACKEND CONFIGURATION
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Enterprise Multi-Tenant FAQ Bot",
    page_icon="🤖",
    layout="wide"
)

# 🔑 SESSION STATE INITIALIZATION
if "session_id" not in st.session_state:
    # Generate a unique session token for this browser tab instance
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_sources" not in st.session_state:
    st.session_state.active_sources = None


# 🗂️ SIDEBAR: Workspace Management & File Uploads
with st.sidebar:
    st.title("⚙️ Workspace Panel")
    
    # Display the current isolated session ID
    st.info(f"**Active Session Partition:**\n`{st.session_state.session_id}`")
    st.caption("All document uploads and chat history are securely sandboxed inside this unique session token.")
    
    st.markdown("---")
    
    # File Uploader Widget
    st.subheader("📥 Ingest Dynamic Context")
    uploaded_file = st.file_uploader(
        "Upload a .txt or .pdf file to train the bot for this session:", 
        type=["txt", "pdf"]
    )
    
    if uploaded_file is not None:
        if st.button("🚀 Process & Vectorize Document", use_container_width=True):
            with st.spinner("Streaming chunks to NVIDIA Embedding pipeline..."):
                try:
                    # Prepare multipart form file payload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    headers = {"X-Session-ID": st.session_state.session_id}
                    
                    # Call FastAPI dynamic ingestion endpoint
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/upload", 
                        files=files, 
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        st.success(f"✅ Context parsed! {uploaded_file.name} is now live in your workspace.")
                    else:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"❌ Ingestion Failed: {error_detail}")
                except Exception as e:
                    st.error(f"❌ Connection error: {str(e)}")

    st.markdown("---")
    
    # Reset/Clear Options
    st.subheader("🧹 Workspace Cleanup")
    if st.button("Clear Chat Window State", use_container_width=True):
        st.session_state.messages = []
        st.session_state.active_sources = None
        st.rerun()

    if st.button("🗑️ Wipe Global Vector DB (Admin)", use_container_width=True, type="secondary"):
        with st.spinner("Dropping collection..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/v1/clear")
                if res.status_code == 200:
                    st.warning("💥 Global Vector Store wiped entirely.")
                else:
                    st.error("Failed to clear DB.")
            except Exception as e:
                st.error(f"Error: {e}")


# 💬 MAIN INTERFACE: Streaming Chat Engine
st.title("🤖 Enterprise Multi-Tenant FAQ Bot")
st.markdown("Ask general questions, standard FAQs, or query details out of your uploaded dynamic documents.")

# 📜 Render Existing Chat Log
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ⚡ Live User Interaction Loop
if prompt := st.chat_input("Type your message here..."):
    # Display user input inside the panel
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Store message in state history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Build a clean conversion format payload for history matching
    formatted_history = [
        {"role": msg["role"], "role": "assistant" if msg["role"] == "assistant" else "user", "content": msg["content"]}
        for msg in st.session_state.messages[:-1]
    ]

    # Setup the JSON request body
    chat_payload = {
        "question": prompt,
        "history": formatted_history,
        "session_id": st.session_state.session_id
    }

    # Stream the incoming chunks from FastAPI
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        sources_found = []

        try:
            # Open persistent stream connection to FastAPI router
            with requests.post(f"{BACKEND_URL}/api/v1/chat", json=chat_payload, stream=True) as response:
                if response.status_code == 500:
                    st.error("The streaming backend pipeline returned a fatal exception.")
                
                for line in response.iter_lines():
                    if line:
                        # Decode raw byte lines from incoming NDJSON data stream
                        decoded_line = line.decode('utf-8')
                        chunk_data = json.loads(decoded_line)
                        
                        # 📦 Handle Retrieved Data Sources
                        if chunk_data.get("type") == "sources":
                            sources_found = chunk_data.get("content", [])
                        
                        # ⚡ Handle Live Text Tokens
                        elif chunk_data.get("type") == "token":
                            full_response += chunk_data.get("content", "")
                            # Live redraw token progression
                            response_placeholder.markdown(full_response + "▌")
            
            # Lock final markdown block state rendering without cursor character
            response_placeholder.markdown(full_response)
            
            # Render Source Documents in an Accordion if present
            if sources_found:
                with st.expander("📚 View Retrieved Reference Sources"):
                    for idx, src in enumerate(sources_found):
                        src_name = src.get("metadata", {}).get("source", "Global Base FAQ")
                        st.markdown(f"**Source [{idx+1}]:** `{src_name}`")
                        st.caption(src.get("content", ""))
            
            # Save assistant milestone string state safely 
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as conn_err:
            st.error(f"Streaming error or dropped server connection: {str(conn_err)}")