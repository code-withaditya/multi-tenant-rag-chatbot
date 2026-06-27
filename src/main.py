import os
import json
import io
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pypdf import PdfReader  
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage  
from src.database import VectorDBManager
from src.engine import build_rag_chain

# Import both tracking/management files
import document_manager as dm
import chat_manager as cm

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists("./chroma_db"):
        print("Initializing Vector Database...")
        db_manager = VectorDBManager()
        db_manager.initialize_db("data/faqs.json")
    yield

app = FastAPI(title="Enterprise FAQ Bot Engine", version="1.0", lifespan=lifespan)

# --- Request Validation Models ---
class QueryRequest(BaseModel):
    question: str
    history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = "default_session"  

class RenameSessionRequest(BaseModel):
    title: str

class FeedbackRequest(BaseModel):
    feedback: str


# =====================================================================
# 💾 PERSISTENT CHAT THREADS & FEEDBACK (API V1)
# =====================================================================

@app.post("/api/v1/chat/sessions")
async def create_new_session_endpoint():
    """Generates a brand new independent conversation partition."""
    return cm.create_chat_session()


@app.get("/api/v1/chat/sessions")
async def list_all_sessions_endpoint():
    """Retrieves all historical conversational logs sorted newest first."""
    return cm.get_all_sessions()


@app.put("/api/v1/chat/sessions/{session_id}")
async def rename_session_endpoint(session_id: str, payload: RenameSessionRequest):
    """Modifies conversation string titles inside database tracking schemas."""
    cm.rename_chat_session(session_id, payload.title)
    return {"status": "success", "message": "Conversation label updated."}


@app.delete("/api/v1/chat/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Purges conversation logging indexes, messages, and elements completely."""
    cm.delete_chat_session(session_id)
    return {"status": "success", "message": f"Session '{session_id}' deleted."}


@app.get("/api/v1/chat/sessions/{session_id}/history")
async def get_session_history_endpoint(session_id: str):
    """Returns chronologically ordered arrays matching a historical log partition."""
    return cm.get_session_history(session_id)


@app.post("/api/v1/chat/messages/{message_id}/feedback")
async def message_feedback_endpoint(message_id: int, payload: FeedbackRequest):
    """Registers thumbs evaluation flags (thumbs_up, thumbs_down, none)."""
    if payload.feedback not in ["thumbs_up", "thumbs_down", "none"]:
        raise HTTPException(status_code=400, detail="Invalid target evaluation state option.")
    cm.submit_message_feedback(message_id, payload.feedback)
    return {"status": "success", "message": f"Feedback status registered as '{payload.feedback}'."}


# =====================================================================
# 📂 SESSION-ISOLATED DOCUMENT MANAGEMENT ENDPOINTS (API V1)
# =====================================================================

@app.post("/api/v1/upload")
async def upload_file_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    x_session_id: Optional[str] = Header(None)  
):
    try:
        target_session = x_session_id or "default_session"
        
        # Quarantine files in a session-specific subdirectory
        session_storage_path = os.path.join(dm.STORAGE_DIR, target_session)
        os.makedirs(session_storage_path, exist_ok=True)
        file_path = os.path.join(session_storage_path, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)
        
        # Associate log entries with specific session scopes
        dm.add_document(file.filename, file_size, target_session)
        
        # Background threads chunk and extract text without breaking user response loop
        background_tasks.add_task(
            dm.process_and_embed_background, 
            file.filename, file_path, target_session
        )
        
        return {
            "status": "success", 
            "message": f"Successfully cached '{file.filename}'. Processing pipeline started."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion scheduling failed: {str(e)}")


@app.get("/api/v1/documents")
async def list_documents_endpoint(x_session_id: Optional[str] = Header(None)):
    target_session = x_session_id or "default_session"
    return dm.get_all_documents(target_session)


@app.get("/api/v1/documents/preview/{filename}")
async def preview_document_endpoint(filename: str, session_id: Optional[str] = None):
    target_session = session_id or "default_session"
    file_path = os.path.join(dm.STORAGE_DIR, target_session, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested file asset does not exist on disk storage.")
    return FileResponse(file_path)


@app.delete("/api/v1/documents/{filename}")
async def delete_document_endpoint(filename: str, x_session_id: Optional[str] = Header(None)):
    target_session = x_session_id or "default_session"
    file_path = os.path.join(dm.STORAGE_DIR, target_session, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    dm.remove_document_meta(filename, target_session)
    return {"status": "success", "message": f"'{filename}' has been completely purged from your workspace."}


# =====================================================================
# 🗑️ ADMIN DATABASE RESET ENDPOINT
# =====================================================================
@app.post("/api/v1/clear")
async def clear_database_endpoint():
    db_manager = VectorDBManager()
    if db_manager.clear_db():
        return {"status": "success", "message": "Vector database cleared successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to drop vector database collection.")


# =====================================================================
# ⚡ STREAMING CHAT ROUTER WITH SYSTEM AUTOMATIC LOGGING
# =====================================================================
@app.post("/api/v1/chat")
async def chat_endpoint(payload: QueryRequest):
    try:
        search_query = payload.question
        chat_history = []
        target_session = payload.session_id or "default_session"

        # 1. Capture and commit user prompt text instantly to history ledger
        user_msg_meta = cm.add_chat_message(target_session, "user", payload.question)
        
        if payload.history and len(payload.history) > 0:
            for msg in payload.history:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))
            
            try:
                rephrase_llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")
                history_context = ""
                for msg in payload.history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    history_context += f"{role}: {msg['content']}\n"
                
                condense_prompt = (
                    f"Given the following chat history and a follow-up question, "
                    f"rephrase the follow-up question into a standalone query.\n\n"
                    f"Chat History:\n{history_context}\n"
                    f"Follow-up Question: {payload.question}\n\n"
                    f"Standalone Query:"
                )
                
                llm_response = rephrase_llm.invoke(condense_prompt)
                search_query = llm_response.content.strip()
                
            except Exception as context_error:
                print(f"⚠️ Memory rephrasing failed: {context_error}")
                search_query = payload.question

        rag_chain = build_rag_chain(session_id=target_session)

        async def event_generator():
            full_ai_response = ""
            ai_msg_id = None
            ai_timestamp = user_msg_meta["timestamp"]

            # Emit initial layout metadata trace so frontend maps human metrics instantly
            yield json.dumps({
                "type": "metadata", 
                "timestamp": user_msg_meta["timestamp"]
            }) + "\n"

            async for chunk in rag_chain.astream({"input": search_query, "chat_history": chat_history}):
                if "context" in chunk:
                    sources_payload = [
                        {"content": doc.page_content, "metadata": doc.metadata}
                        for doc in chunk["context"]
                    ]
                    yield json.dumps({"type": "sources", "content": sources_payload}) + "\n"
                
                if "answer" in chunk:
                    token_content = chunk["answer"]
                    full_ai_response += token_content
                    yield json.dumps({"type": "token", "content": token_content}) + "\n"

            # 2. Complete token accumulation stream execution, save AI response block to SQLite
            if full_ai_response.strip():
                ai_meta = cm.add_chat_message(target_session, "assistant", full_ai_response)
                ai_msg_id = ai_meta["message_id"]
                ai_timestamp = ai_meta["timestamp"]

            # Emit final structural trace passing along tracking indices 
            yield json.dumps({
                "type": "completion", 
                "message_id": ai_msg_id, 
                "timestamp": ai_timestamp
            }) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat streaming pipeline failed: {str(e)}")