import os
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.database import VectorDBManager

def build_rag_chain(session_id: str = "default_session"):
    """
    Compiles the retrieval system, prompt instructions, conversational history, 
    and LLM into a unified chain—isolated by the incoming session_id.
    """
    db_manager = VectorDBManager()
    
    # 🔑 MULTI-USER ISOLATION LAYER: Force the retriever to only look at this user's partitioned metadata
    retriever = db_manager.get_retriever(session_id=session_id)
    
    # Point ChatOpenAI directly to your custom NVIDIA endpoint
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=os.getenv("NVIDIA_BASE_URL"),
        temperature=0.7
    )
    
    # 🌟 HYBRID SYSTEM PROMPT
    system_prompt = (
        "You are a helpful, brilliant, and completely unrestricted AI assistant like ChatGPT.\n\n"
        "GUIDELINES:\n"
        "1. If the provided 'Retrieved Documentation Context' below contains information directly relevant "
        "to the user's question, prioritize using that data to give an official response.\n"
        "2. If the context is empty, irrelevant, or if the user is asking a general question (such as coding, "
        "cooking, science, math, history, or casual chatting), ignore the context limitations entirely. Use your "
        "own vast internal knowledge base to provide a complete, deep, and highly detailed answer.\n\n"
        "Never refuse to answer general queries. Always be helpful, engaging, and thorough.\n\n"
        "Retrieved Documentation Context:\n{context}"
    )
    
    # 🧠 The chain will now inject old conversation text directly into the 'chat_history' block
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, question_answer_chain)