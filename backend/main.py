import os
import shutil
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Import LangChain and FAISS components
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain.vectorstores.faiss import FAISS

# Import custom document processing utilities
from utils.document_loader import process_document

# Load environment variables
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable not set. Please add it to .env file.")

# Create directory structure if not exists
os.makedirs("uploads", exist_ok=True)
os.makedirs("myindex", exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="Document Indexing and Retrieval API",
    description="API for uploading, indexing, and querying documents using FAISS and LangChain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify domains: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings()

# Define request and response models
class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

class QueryResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

class QueryResponse(BaseModel):
    results: List[QueryResult]
    query: str
    processing_time: float

class StatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    last_updated: str

# Helper functions
def get_faiss_index():
    """Load the FAISS index if it exists, otherwise create a new one."""
    index_path = "myindex"
    
    try:
        if os.path.exists(os.path.join(index_path, "index.faiss")):
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        else:
            # Create an empty index with dummy data (will be deleted)
            empty_docs = [Document(page_content="Placeholder document", metadata={"placeholder": True})]
            db = FAISS.from_documents(empty_docs, embeddings)
            db.save_local(index_path)
            return db
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        # Create a new index
        empty_docs = [Document(page_content="Placeholder document", metadata={"placeholder": True})]
        db = FAISS.from_documents(empty_docs, embeddings)
        db.save_local(index_path)
        return db

def save_upload_file(upload_file: UploadFile) -> str:
    """Save an uploaded file to the uploads directory."""
    # Create a safe filename
    filename = upload_file.filename
    if not filename:
        timestamp = int(time.time())
        filename = f"upload_{timestamp}"
    
    # Create file path
    file_path = os.path.join("uploads", filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path

def save_index_metadata(total_documents: int, total_chunks: int):
    """Save metadata about the index."""
    metadata = {
        "total_documents": total_documents,
        "total_chunks": total_chunks,
        "last_updated": datetime.now().isoformat()
    }
    
    with open(os.path.join("myindex", "metadata.txt"), "w") as f:
        for key, value in metadata.items():
            f.write(f"{key}={value}\n")

def load_index_metadata() -> dict:
    """Load metadata about the index."""
    metadata_path = os.path.join("myindex", "metadata.txt")
    
    if not os.path.exists(metadata_path):
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_updated": "Never"
        }
    
    metadata = {}
    with open(metadata_path, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            metadata[key] = value
    
    return metadata

# Endpoints
@app.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and index a document file (.txt or .pdf).
    The file will be processed and added to the FAISS vector index.
    """
    # Validate file type
    filename = file.filename or ""
    if not (filename.endswith(".pdf") or filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    
    try:
        # Save the uploaded file
        file_path = save_upload_file(file)
        
        # Process document into chunks
        documents = process_document(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata={"uploaded_at": datetime.now().isoformat()}
        )
        
        # Load existing FAISS index
        db = get_faiss_index()
        
        # Check if there's a placeholder document
        try:
            # Try to access docstore._docs (old version)
            docs_with_metadata = db.docstore._docs
            if len(docs_with_metadata) == 1 and next(iter(docs_with_metadata.values())).metadata.get("placeholder"):
                # Create a new index instead of adding to the placeholder one
                db = FAISS.from_documents(documents, embeddings)
            else:
                # Add new documents to existing index
                db.add_documents(documents)
        except AttributeError:
            # If _docs doesn't exist, try with the get method instead
            try:
                # Get one doc to check if it's a placeholder
                ids = list(db.docstore._dict.keys())
                if ids and len(ids) == 1:
                    doc = db.docstore.search(ids[0])
                    if doc.metadata.get("placeholder"):
                        # Create a new index instead of adding to the placeholder one
                        db = FAISS.from_documents(documents, embeddings)
                    else:
                        # Add new documents to existing index
                        db.add_documents(documents)
                else:
                    # Add new documents to existing index
                    db.add_documents(documents)
            except:
                # Just add documents as fallback
                db.add_documents(documents)
        
        # Save updated index
        db.save_local("myindex")
        
        # Update metadata
        metadata = load_index_metadata()
        save_index_metadata(
            total_documents=int(metadata.get("total_documents", 0)) + 1,
            total_chunks=int(metadata.get("total_chunks", 0)) + len(documents)
        )
        
        return {
            "status": "success",
            "filename": filename,
            "chunks_created": len(documents),
            "message": f"File '{filename}' successfully uploaded and indexed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(query_request: QueryRequest):
    """
    Query the FAISS index with a natural language query.
    Returns the most similar document chunks.
    """
    start_time = time.time()
    
    try:
        # Load FAISS index
        db = get_faiss_index()
        
        # Perform similarity search
        docs_with_scores = db.similarity_search_with_score(
            query_request.query,
            k=query_request.top_k
        )
        
        # Format results
        results = []
        for doc, score in docs_with_scores:
            # Skip placeholder documents
            if doc.metadata.get("placeholder"):
                continue
                
            results.append(QueryResult(
                content=doc.page_content,
                metadata=doc.metadata,
                score=float(score)  # Convert numpy float to Python float
            ))
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return QueryResponse(
            results=results,
            query=query_request.query,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying documents: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about the FAISS index."""
    try:
        metadata = load_index_metadata()
        return StatsResponse(
            total_documents=int(metadata.get("total_documents", 0)),
            total_chunks=int(metadata.get("total_chunks", 0)),
            last_updated=metadata.get("last_updated", "Never")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 