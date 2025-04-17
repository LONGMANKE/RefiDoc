import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader

def load_text_file(file_path: str) -> str:
    """Load and extract text from a .txt file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        return file.read()

def load_pdf_file(file_path: str) -> str:
    """Load and extract text from a PDF file using PyPDF2."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def load_document(file_path: str) -> str:
    """Load document based on file extension."""
    _, file_extension = os.path.splitext(file_path)
    
    if file_extension.lower() == '.pdf':
        return load_pdf_file(file_path)
    elif file_extension.lower() == '.txt':
        return load_text_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    Split text into manageable chunks for embedding.
    
    Args:
        text: The document text to split
        chunk_size: Maximum size of each text chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of Document objects
    """
    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    # Split text into chunks
    chunks = text_splitter.split_text(text)
    
    # Convert to Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "chunk_size": len(chunk)
            }
        )
        documents.append(doc)
    
    return documents

def process_document(file_path: str, metadata: Dict[str, Any] = None, 
                    chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    Process a document file into Document objects with metadata.
    
    Args:
        file_path: Path to the document file
        metadata: Additional metadata to add to each document
        chunk_size: Maximum size of each text chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of Document objects
    """
    # Extract base filename for metadata
    filename = os.path.basename(file_path)
    
    # Initialize metadata if not provided
    if metadata is None:
        metadata = {}
    
    # Add file info to metadata
    file_metadata = {
        "source": filename,
        "file_path": file_path,
        **metadata
    }
    
    # Load document text
    text = load_document(file_path)
    
    # Split into chunks
    documents = split_text(text, chunk_size, chunk_overlap)
    
    # Add metadata to each document
    for doc in documents:
        doc.metadata.update(file_metadata)
    
    return documents 