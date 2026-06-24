import json
import os
from openai import OpenAI
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter  

class NvidiaCompatibleEmbeddings(Embeddings):
    """
    Custom embedding processor that bypasses LangChain's internal tokenization middleware
    to pass raw text strings and asymmetric type configurations directly to NVIDIA NIM.
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a list of documentation chunks using the 'passage' type."""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model,
            extra_body={"input_type": "passage"}
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        """Embeds a live user search query using the 'query' type."""
        response = self.client.embeddings.create(
            input=[text],
            model=self.model,
            extra_body={"input_type": "query"}
        )
        return response.data[0].embedding


class VectorDBManager:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.embeddings = NvidiaCompatibleEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nvidia/llama-nemotron-embed-1b-v2"),
            api_key=os.getenv("NVIDIA_API_KEY"),
            base_url=os.getenv("NVIDIA_BASE_URL")
        )
        self.persist_directory = persist_directory
        self.vector_store = None

    def _ensure_vector_store(self):
        """🛡️ Internal safeguard to ensure the Chroma instance is actively loaded in memory."""
        if self.vector_store is None:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

    def initialize_db(self, faq_filepath: str):
        """
        Loads incoming JSON FAQs, formats them into searchable LangChain Documents,
        and saves them locally via ChromaDB stamped with a 'global' scope.
        """
        if not os.path.exists(faq_filepath):
            raise FileNotFoundError(f"Could not find FAQ data resource file at: {faq_filepath}")

        with open(faq_filepath, 'r') as f:
            faq_data = json.load(f)
        
        documents = []
        for item in faq_data:
            page_content = f"Question: {item['question']}\nAnswer: {item['answer']}"
            
            # 🔑 Added session_id: "global" so these base FAQs are accessible to all users
            metadata = {
                "category": item["category"], 
                "faq_id": item["id"],
                "session_id": "global"
            }
            documents.append(Document(page_content=page_content, metadata=metadata))
        
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        print(f"🚀 Vector DB successfully initialized with {len(documents)} FAQs via NVIDIA Embeddings.")

    def get_retriever(self, session_id: str = "default_session"):
        """
        Loads the localized database and converts it into a queryable retriever layer 
        strictly filtered by the active session identity.
        """
        self._ensure_vector_store()
        
        # 🔑 MULTI-TENANCY FILTER: Look for global baseline data OR this specific user's uploads
        meta_filter = {
            "$or": [
                {"session_id": "global"},
                {"session_id": session_id}
            ]
        }
        
        return self.vector_store.as_retriever(
            search_kwargs={
                "k": 2,
                "filter": meta_filter
            }
        )

    def add_text_to_db(self, text: str, filename: str, session_id: str = "default_session"):
        """
        📥 Chunks raw text from dynamic frontend uploads, computes NVIDIA embeddings,
        and appends them directly into the live database marked with the owner's session ID.
        """
        self._ensure_vector_store()

        # 1. Break the document down into semantic pieces
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
        chunks = text_splitter.split_text(text)

        # 2. Package raw strings into formal LangChain Document structures
        documents = []
        for idx, chunk in enumerate(chunks):
            # 🔑 Stamping chunk dictionary metadata with the active session tracking ID
            metadata = {
                "source": filename,
                "category": "Dynamic Upload",
                "chunk_index": idx,
                "session_id": session_id
            }
            documents.append(Document(page_content=chunk, metadata=metadata))

        # 3. Stream the newly generated embeddings straight into the persistent store
        self.vector_store.add_documents(documents)
        print(f"⚡ Successfully indexed {len(documents)} dynamic chunks from raw file: '{filename}' for session '{session_id}'")

    def clear_db(self):
        """🗑️ Completely wipes out the existing vector store collection securely on disk and in RAM."""
        try:
            self._ensure_vector_store()
            self.vector_store.delete_collection()
            self.vector_store = None
            print("🗑️ Vector database collection successfully cleared!")
            return True
        except Exception as e:
            print(f"❌ Failed to clear vector database: {e}")
            return False