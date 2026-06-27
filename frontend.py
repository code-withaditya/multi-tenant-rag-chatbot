import streamlit as st
import streamlit.components.v1 as components
import requests
import json

# 🌐 GLOBAL PAGE CONFIGURATION
st.set_page_config(
    page_title="Enterprise Multi-Tenant FAQ Bot",
    page_icon="🤖",
    layout="wide"
)

# =====================================================================
# 🎨 DESIGN SYSTEM LAYER: GLASSMORPHISM & ANIMATED MICRO-INTERACTIONS
# =====================================================================
st.markdown("""
<style>
    /* Global Smooth Scrolling and Base Font Stack */
    html, body, [data-testid="stAppViewContainer"] {
        scroll-behavior: smooth;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 🎭 Frosted Glassmorphism Sidebar Architecture */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    
    @media (prefers-color-scheme: light) {
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.75) !important;
            border-right: 1px solid rgba(0, 0, 0, 0.06) !important;
        }
    }

    /* ✨ Elegant Entry Animations & Elevation for Chat Bubbles */
    [data-testid="stChatMessage"] {
        animation: fadeInRise 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        border-radius: 16px !important;
        margin-bottom: 14px !important;
        padding: 1.15rem !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    
    [data-testid="stChatMessage"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
    }

    @keyframes fadeInRise {
        from {
            opacity: 0;
            transform: translateY(16px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* ⚡ Glowing Animated Streaming Caret Effect */
    .streaming-caret {
        display: inline-block;
        color: #4A90E2;
        font-weight: bold;
        margin-left: 2px;
        animation: pulseCaret 0.8s infinite steps(2, start);
    }
    @keyframes pulseCaret {
        0%, 100% { opacity: 0; }
        50% { opacity: 1; }
    }

    /* ⏳ Modern Glowing Typing Indicator Dots */
    .typing-container {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 12px 18px;
        background: rgba(74, 144, 226, 0.06);
        border: 1px solid rgba(74, 144, 226, 0.15);
        border-radius: 14px;
        width: fit-content;
        margin-top: 5px;
        animation: pulseContainer 2s infinite ease-in-out;
    }
    .typing-dot {
        width: 7px;
        height: 7px;
        background: #4A90E2;
        border-radius: 50%;
        animation: bounceDot 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes bounceDot {
        0%, 80%, 100% { transform: scale(0.3); opacity: 0.4; }
        40% { transform: scale(1.1); opacity: 1; }
    }
    @keyframes pulseContainer {
        0%, 100% { box-shadow: 0 0 10px rgba(74, 144, 226, 0.05); }
        50% { box-shadow: 0 0 18px rgba(74, 144, 226, 0.15); }
    }

    /* 📱 Responsive Mobile Layout Compression */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column !important;
        }
        [data-testid="stChatMessage"] {
            padding: 0.85rem !important;
        }
    }

    /* 📂 Fluid Drag-and-Drop Uploader Area Customization */
    [data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #4A90E2 !important;
        background: rgba(74, 144, 226, 0.02) !important;
        border-radius: 14px !important;
        padding: 2rem 1rem !important;
        transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        background: rgba(74, 144, 226, 0.07) !important;
        border-color: #357ABD !important;
        transform: scale(1.005);
    }
    
    /* 🎯 Keyboard Shortcut Legend Badge Style */
    .shortcut-badge {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 11px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 🎯 KEYBOARD SHORTCUTS JAVASCRIPT INJECTION
# =====================================================================
components.html("""
<script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        // 1. New Sandbox Session Track: Ctrl + Alt + N
        if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'n') {
            e.preventDefault();
            const buttons = Array.from(doc.querySelectorAll('button'));
            const targetBtn = buttons.find(el => el.textContent.includes('Start New Conversation'));
            if (targetBtn) targetBtn.click();
        }
        // 2. Fast Input Box Focus Navigation Focus: Ctrl + Alt + C
        if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'c') {
            e.preventDefault();
            const chatInput = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) chatInput.focus();
        }
    });
</script>
""", height=0, width=0)

# 🌐 BACKEND CORE API URL
BACKEND_URL = "http://localhost:8000"

# =====================================================================
# 🔑 CORE SYSTEM STATE INITIALIZATION
# =====================================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = "default_session"
if "session_title" not in st.session_state:
    st.session_state.session_title = "Default Conversation"
if "renaming_session_id" not in st.session_state:
    st.session_state.renaming_session_id = None
if "regen_prompt" not in st.session_state:
    st.session_state.regen_prompt = None

try:
    res = requests.get(f"{BACKEND_URL}/api/v1/chat/sessions")
    sessions = res.json() if res.status_code == 200 else []
    if sessions and st.session_state.session_id == "default_session":
        st.session_state.session_id = sessions[0]["session_id"]
        st.session_state.session_title = sessions[0]["title"]
except:
    sessions = []


# =====================================================================
# 🗂️ SIDEBAR: THREADS, NAVIGATION, EXPORTS & ADMIN PANEL
# =====================================================================
with st.sidebar:
    st.title("⚙️ Workspace Panel")
    
    # ➕ Spawn Fresh Isolated Sandbox Workspace Partition
    if st.button("➕ Start New Conversation", use_container_width=True, type="primary"):
        try:
            res = requests.post(f"{BACKEND_URL}/api/v1/chat/sessions")
            if res.status_code == 200:
                new_session = res.json()
                st.session_state.session_id = new_session["session_id"]
                st.session_state.session_title = new_session["title"]
                st.toast("⚡ Fresh conversational segment loaded!")
                st.rerun()
        except Exception:
            st.error("Backend offline. Could not spawn session thread.")

    st.markdown("---")
    
    # 🧭 Navigation Systems Manager
    st.subheader("🧭 Navigation")
    navigation = st.radio(
        "Go to page:",
        ["💬 Chat Assistant", "📂 Manage Documents"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 📜 SQLite Thread Catalog Index Sync Engine
    st.subheader("🗂️ Conversation Threads")
    if not sessions:
        st.caption("No historical message tracks logged yet.")
    
    for sess in sessions:
        sid = sess["session_id"]
        title = sess["title"]
        is_active = (sid == st.session_state.session_id)
        
        col_select, col_edit, col_del = st.columns([6, 1.5, 1.5])
        button_label = f"💬 {title}" if not is_active else f"👉 {title}"
        
        if col_select.button(button_label, key=f"sel_{sid}", use_container_width=True):
            st.session_state.session_id = sid
            st.session_state.session_title = title
            st.rerun()
            
        if col_edit.button("✏️", key=f"edt_{sid}", help="Modify thread title string"):
            st.session_state.renaming_session_id = sid
            st.session_state.rename_placeholder = title
            st.rerun()
            
        if col_del.button("🗑️", key=f"del_thread_{sid}", help="Purge thread from memory database"):
            try:
                requests.delete(f"{BACKEND_URL}/api/v1/chat/sessions/{sid}")
                if st.session_state.session_id == sid:
                    st.session_state.session_id = "default_session"
                    st.session_state.session_title = "Default Conversation"
                st.toast("Purged conversation record successfully.")
                st.rerun()
            except:
                st.error("Failed to drop record.")

    if st.session_state.renaming_session_id:
        st.write("---")
        st.caption("✏️ Modify Selected Thread Label Name:")
        new_title_text = st.text_input("New Name:", value=st.session_state.rename_placeholder, label_visibility="collapsed")
        
        c_save, c_cancel = st.columns(2)
        if c_save.button("💾 Apply", use_container_width=True):
            if new_title_text.strip():
                requests.put(
                    f"{BACKEND_URL}/api/v1/chat/sessions/{st.session_state.renaming_session_id}",
                    json={"title": new_title_text.strip()}
                )
                if st.session_state.session_id == st.session_state.renaming_session_id:
                    st.session_state.session_title = new_title_text.strip()
                st.session_state.renaming_session_id = None
                st.rerun()
        if c_cancel.button("Cancel", use_container_width=True):
            st.session_state.renaming_session_id = None
            st.rerun()

    # =====================================================================
    # 📤 DATA EXPORT COMPILER INTERFACES
    # =====================================================================
    st.markdown("---")
    st.subheader("📦 Export Conversation")
    
    try:
        hist_res = requests.get(f"{BACKEND_URL}/api/v1/chat/sessions/{st.session_state.session_id}/history")
        active_history = hist_res.json() if hist_res.status_code == 200 else []
    except:
        active_history = []

    if active_history:
        export_txt = f"=== CHAT ENGINE LOG: {st.session_state.session_title} ===\n\n"
        export_md = f"# Conversational Log Export: {st.session_state.session_title}\n\n"
        
        for msg in active_history:
            speaker = "👤 User Prompt" if msg["role"] == "user" else "🤖 System Response"
            export_txt += f"[{msg['timestamp']}] {speaker}:\n{msg['content']}\n\n"
            export_md += f"### 🗓️ [{msg['timestamp']}] {speaker}\n{msg['content']}\n\n---\n"
            
        st.download_button(
            label="📝 Download Plain Text (.txt)",
            data=export_txt,
            file_name=f"{st.session_state.session_title.lower().replace(' ', '_')}_history.txt",
            mime="text/plain",
            use_container_width=True
        )
        st.download_button(
            label="Ⓜ️ Download Markdown (.md)",
            data=export_md,
            file_name=f"{st.session_state.session_title.lower().replace(' ', '_')}_history.md",
            mime="text/markdown",
            use_container_width=True
        )
    else:
        st.caption("No text logs available to export inside this thread context partition yet.")

    # 🎯 KEYBOARD SHORTCUT REFERENCE LEGEND
    st.markdown("---")
    st.subheader("🎯 Productivity Hotkeys")
    st.markdown("""
    * <span class="shortcut-badge">Ctrl+Alt+N</span> New Thread
    * <span class="shortcut-badge">Ctrl+Alt+C</span> Focus Chat
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🧹 Workspace Cleanup")
    if st.button("🗑️ Wipe Global Vector DB (Admin)", use_container_width=True, type="secondary"):
        with st.spinner("Dropping database engine collection states..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/v1/clear")
                if res.status_code == 200:
                    st.warning("💥 Global Vector Store wiped entirely.")
                else:
                    st.error("Failed to clear DB.")
            except Exception as e:
                st.error(f"Error: {e}")


# =====================================================================
# 🤖 MAIN ENGINE HEADER DISPLAY
# =====================================================================
st.title("🤖 Enterprise Multi-Tenant FAQ Bot")
st.caption(f"🔒 Isolated Session Track Context Partition Id: `{st.session_state.session_id}`")

# ----------------------------------------------------------------------
# 💬 PAGE 1: CHAT ASSISTANT
# ----------------------------------------------------------------------
if navigation == "💬 Chat Assistant":
    st.write(f"### Current Workspace: `{st.session_state.session_title}`")
    
    # 📜 Interactive Chat Rendering Loop
    last_user_prompt = None
    for idx, message in enumerate(active_history):
        if message["role"] == "user":
            last_user_prompt = message["content"]
            avatar_icon = "👤"
        else:
            avatar_icon = "🤖"
            
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.markdown(message["content"])
            
            c_meta, c_actions = st.columns([8, 2])
            c_meta.markdown(f"<span style='color:gray; font-size:12px;'>⏰ Saved at {message['timestamp']}</span>", unsafe_allow_html=True)
            
            if message["role"] == "assistant":
                msg_id = message["id"]
                current_feedback = message.get("feedback", "none")
                
                with c_actions:
                    act_col1, act_col2, act_col3, act_col4 = st.columns(4)
                    
                    if act_col1.button("📋", key=f"cp_{msg_id}_{idx}", help="Copy response text content block"):
                        st.copy_to_clipboard(message["content"])
                        st.toast("Copied text response to clipboard!")
                        
                    up_style = "⭐" if current_feedback == "thumbs_up" else "👍"
                    if act_col2.button(up_style, key=f"up_{msg_id}_{idx}", help="Log positive accuracy appraisal"):
                        requests.post(f"{BACKEND_URL}/api/v1/chat/messages/{msg_id}/feedback", json={"feedback": "thumbs_up"})
                        st.toast("Logged alignment score status.")
                        st.rerun()
                        
                    down_style = "🚨" if current_feedback == "thumbs_down" else "👎"
                    if act_col3.button(down_style, key=f"dn_{msg_id}_{idx}", help="Flag response variance anomaly"):
                        requests.post(f"{BACKEND_URL}/api/v1/chat/messages/{msg_id}/feedback", json={"feedback": "thumbs_down"})
                        st.toast("Flagged context accuracy review indicator.")
                        st.rerun()
                        
                    if act_col4.button("🔄", key=f"rg_{msg_id}_{idx}", help="Regenerate this specific query payload"):
                        if last_user_prompt:
                            st.session_state.regen_prompt = last_user_prompt
                            st.rerun()

    # ⌨️ Interaction Loop Interceptor
    prompt = st.chat_input("Type your message here...", key="chat_page_input")
    
    if st.session_state.regen_prompt:
        prompt = st.session_state.regen_prompt
        st.session_state.regen_prompt = None
        
    if prompt:
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        formatted_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in active_history
        ]

        chat_payload = {
            "question": prompt,
            "history": formatted_history,
            "session_id": st.session_state.session_id
        }

        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            
            # ⏳ Show animated typing indicator before network streams open
            response_placeholder.markdown("""
                <div class="typing-container">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            """, unsafe_allow_html=True)
            
            full_response = ""
            sources_found = []

            try:
                with requests.post(f"{BACKEND_URL}/api/v1/chat", json=chat_payload, stream=True) as response:
                    if response.status_code == 500:
                        st.error("The streaming backend pipeline returned a fatal exception.")
                    
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            chunk_data = json.loads(decoded_line)
                            
                            if chunk_data.get("type") == "sources":
                                sources_found = chunk_data.get("content", [])
                            elif chunk_data.get("type") == "token":
                                full_response += chunk_data.get("content", "")
                                # ⚡ Render streaming response paired with custom pulsing caret
                                response_placeholder.markdown(f"{full_response}<span class='streaming-caret'>▌</span>", unsafe_allow_html=True)
                
                response_placeholder.markdown(full_response)
                
                if sources_found:
                    with st.expander("📚 View Retrieved Reference Sources"):
                        for s_idx, src in enumerate(sources_found):
                            src_name = src.get("metadata", {}).get("source", "Global Base FAQ")
                            st.markdown(f"**Source [{s_idx+1}]:** `{src_name}`")
                            st.caption(src.get("content", ""))
                st.rerun()
                
            except Exception as conn_err:
                st.error(f"Streaming error or dropped server connection: {str(conn_err)}")


# ----------------------------------------------------------------------
# 📂 PAGE 2: DOCUMENT CONTROL PANEL & DATA INGESTION
# ----------------------------------------------------------------------
elif navigation == "📂 Manage Documents":
    st.subheader("📤 Document Ingestion Portal")
    
    uploaded_files = st.file_uploader(
        "Upload files to automatically chunk, vectorize, and inject into your isolated session memory partition:",
        type=["pdf", "docx", "txt", "md", "csv", "html"],
        accept_multiple_files=True,
        key="document_portal_uploader"
    )

    if uploaded_files:
        if st.button("⚡ Process All Uploaded Files", type="primary", use_container_width=True):
            for file in uploaded_files:
                with st.spinner(f"Streaming chunks of {file.name} to ingestion cluster..."):
                    files = {"file": (file.name, file.getvalue(), file.type)}
                    headers = {"X-Session-ID": st.session_state.session_id}
                    
                    try:
                        res = requests.post(f"{BACKEND_URL}/api/v1/upload", files=files, headers=headers)
                        if res.status_code == 200:
                            st.toast(f"✅ Indexed {file.name} successfully!")
                        else:
                            error_detail = res.json().get('detail', 'Unknown error')
                            st.error(f"❌ Failed to parse {file.name}: {error_detail}")
                    except Exception as e:
                        st.error(f"❌ Transmission Error on {file.name}: {str(e)}")
            st.rerun()

    st.write("---")
    st.subheader("📊 Active Document Control Panel")

    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/documents", headers={"X-Session-ID": st.session_state.session_id})
        docs = response.json() if response.status_code == 200 else []
    except Exception:
        docs = []

    search_query = st.text_input("🔍 Search files by name...", "", key="search_query_bar")
    filtered_docs = [d for d in docs if search_query.lower() in d["filename"].lower()]

    if not filtered_docs:
        st.info("No documents are currently indexed inside this session partition workspace.")
    else:
        cols = st.columns([3, 1.5, 2, 2, 1.5])
        cols[0].markdown("**File Name**")
        cols[1].markdown("**Size**")
        cols[2].markdown("**Upload Date**")
        cols[3].markdown("**Embedding Status**")
        cols[4].markdown("**Actions**")
        
        for d_idx, doc in enumerate(filtered_docs):
            cols = st.columns([3, 1.5, 2, 2, 1.5])
            cols[0].write(doc["filename"])
            cols[1].write(f"{doc.get('size_kb', 0)} KB")
            cols[2].write(doc.get("date", "N/A"))
            
            status = doc.get("status", "Completed")
            if "Failed" in status:
                cols[3].error("❌ Failed")
            elif status == "Completed":
                cols[3].success("✅ Completed")
            else:
                cols[3].warning("⏳ Processing")
                
            with cols[4]:
                act_c1, act_c2 = st.columns(2)
                
                if act_c1.button("🗑️", key=f"del_{doc['filename']}_{d_idx}", help="Wipe file from core RAG memory"):
                    try:
                        requests.delete(f"{BACKEND_URL}/api/v1/documents/{doc['filename']}", headers={"X-Session-ID": st.session_state.session_id})
                        st.toast(f"Purged {doc['filename']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not purge file: {e}")
                    
                if doc["filename"].lower().endswith(".pdf"):
                    if act_c2.button("👁️", key=f"view_{doc['filename']}_{d_idx}", help="Preview PDF layout"):
                        st.session_state["preview_pdf"] = doc["filename"]
                        st.rerun()

        if "preview_pdf" in st.session_state and st.session_state["preview_pdf"]:
            active_file = st.session_state["preview_pdf"]
            st.write("---")
            st.markdown(f"### 📄 Document Live View: `{active_file}`")
            if st.button("Close Preview ❌", key="close_preview_btn"):
                st.session_state["preview_pdf"] = None
                st.rerun()
                
            preview_url = f"{BACKEND_URL}/api/v1/documents/preview/{active_file}?session_id={st.session_state.session_id}"
            st.markdown(f'<iframe src="{preview_url}" width="100%" height="600px" style="border:1px solid #ccc; border-radius:5px;"></iframe>', unsafe_html=True)