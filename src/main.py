import os
import json
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Header  
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pypdf import PdfReader  
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage  
from src.database import VectorDBManager
from src.engine import build_rag_chain

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists("./chroma_db"):
        print("Initializing Vector Database...")
        db_manager = VectorDBManager()
        db_manager.initialize_db("data/faqs.json")
    yield

app = FastAPI(title="Enterprise FAQ Bot Engine", version="1.0", lifespan=lifespan)

class QueryRequest(BaseModel):
    question: str
    history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = "default_session"  


# 📂 DYNAMIC KNOWLEDGE INGESTION ENDPOINT
@app.post("/api/v1/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...), 
    x_session_id: Optional[str] = Header(None)  
):
    """
    Accepts standard multipart form file uploads (.txt or .pdf), extracts raw text 
    contents in-memory, and passes them along with a unique session ID.
    """
    try:
        contents = await file.read()
        filename = file.filename.lower()
        text_data = ""

        # 📄 Process Plain Text Files
        if filename.endswith(".txt"):
            text_data = contents.decode("utf-8")

        # 📕 Process PDF Files In-Memory
        elif filename.endswith(".pdf"):
            pdf_stream = io.BytesIO(contents)
            pdf_reader = PdfReader(pdf_stream)
            
            extracted_pages = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            
            text_data = "\n".join(extracted_pages)
            
            if not text_data.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="The uploaded PDF appears to be empty or contains only non-scanned imagery (OCR required)."
                )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file format. Please upload a valid plain text (.txt) or PDF (.pdf) document."
            )
        
        db_manager = VectorDBManager()
        target_session = x_session_id or "default_session"
        db_manager.add_text_to_db(text_data, filename=file.filename, session_id=target_session)
        
        return {
            "status": "success", 
            "message": f"Successfully vectorized and stored {file.filename} under session context!"
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, 
            detail="File encoding error: Please ensure your text file is saved with valid UTF-8 encoding."
        )
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion pipeline failed: {str(e)}")


# 🗑️ ADMIN DATABASE RESET ENDPOINT
@app.post("/api/v1/clear")
async def clear_database_endpoint():
    """
    Triggers a collection wipe on the vector database.
    """
    db_manager = VectorDBManager()
    if db_manager.clear_db():
        return {"status": "success", "message": "Vector database cleared successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to drop vector database collection.")


# ⚡ LIVE STREAMING CHAT ROUTER
@app.post("/api/v1/chat")
async def chat_endpoint(payload: QueryRequest):
    try:
        search_query = payload.question
        chat_history = []
        
        # Format the conversational history state if it exists
        if payload.history and len(payload.history) > 0:
            for msg in payload.history:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))
            
            # ✨ RESTORED & ALIGNED MEMORY CONTEXT BLOCK
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
                
                # Execute standard LangChain invocation
                llm_response = rephrase_llm.invoke(condense_prompt)
                search_query = llm_response.content.strip()
                
            except Exception as context_error:
                print(f"⚠️ Memory rephrasing failed: {context_error}")
                search_query = payload.question

        # Build execution pipeline tied strictly to this user's workspace partitions
        rag_chain = build_rag_chain(session_id=payload.session_id)

        async def event_generator():
            async for chunk in rag_chain.astream({"input": search_query, "chat_history": chat_history}):
                if "context" in chunk:
                    sources_payload = [
                        {"content": doc.page_content, "metadata": doc.metadata}
                        for doc in chunk["context"]
                    ]
                    yield json.dumps({"type": "sources", "content": sources_payload}) + "\n"
                
                if "answer" in chunk:
                    yield json.dumps({"type": "token", "content": chunk["answer"]}) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat streaming pipeline failed: {str(e)}")