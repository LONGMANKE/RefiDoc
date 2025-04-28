# System Architecture: RefiDoc

This document outlines the system architecture for the RefiDoc application, a Retrieval-Augmented Generation (RAG) system designed for querying documents.

## Overview

The system consists of two main services orchestrated using Docker Compose:

1.  **Frontend:** A Flask-based web application responsible for user interaction, authentication, chat management, and orchestrating the RAG pipeline.
2.  **Backend:** A FastAPI-based API service responsible for document ingestion, processing, indexing, and retrieval.

## Components

### 1. Frontend Service (`frontend/`)

*   **Framework:** Flask
*   **Database:** SQLite (`frontend/instance/chat_app.db`) using Flask-SQLAlchemy
*   **Port:** 5000
*   **Key Responsibilities:**
    *   User Interface (HTML templates in `frontend/templates/`, static assets in `frontend/static/`)
    *   User Authentication & Authorization (Login, Registration, Admin roles)
    *   Chat Session Management (Storing/retrieving chat history)
    *   Document Metadata Management (Tracking uploaded files, versions, uploaders)
    *   RAG Orchestration:
        *   Sends user queries to the Backend API (`/query`).
        *   Receives context (relevant document chunks) from the Backend.
        *   Constructs prompts using retrieved context.
        *   Interacts with Azure OpenAI Chat Completion API to generate final answers.
        *   Displays chat messages and results.
    *   Document Management UI (Admin only): Uploading, viewing, deleting, downloading, previewing documents.
    *   Sends documents to the Backend API for processing (`/upload`).

### 2. Backend Service (`backend/`)

*   **Framework:** FastAPI
*   **Vector Store:** FAISS (`backend/myindex/`)
*   **Embeddings:** Azure OpenAI Embeddings (via LangChain)
*   **Port:** 8000
*   **Key Responsibilities:**
    *   Document Ingestion API (`/upload`):
        *   Receives files (PDF, TXT) from the Frontend.
        *   Saves files locally (`backend/uploads/`).
        *   Uses `utils/document_loader` for text extraction and chunking.
        *   Generates vector embeddings for chunks using Azure OpenAI Embeddings.
        *   Adds embeddings to the FAISS vector index.
        *   Updates index metadata (`backend/myindex/metadata.txt`).
    *   Document Retrieval API (`/query`):
        *   Receives text queries from the Frontend.
        *   Embeds the query using Azure OpenAI Embeddings.
        *   Performs similarity search against the FAISS index.
        *   Returns the top `k` relevant document chunks (content and metadata).
    *   Utility Endpoints: `/stats` (index info), `/files` (list uploads), `/files/{filename}` (delete upload - *Note: Index update for deletion might be missing*), `/health` (health check).

### 3. External Services

*   **Azure OpenAI Service:**
    *   Used by the Backend for generating text embeddings (`AzureOpenAIEmbeddings`).
    *   Used by the Frontend for generating chat completions based on retrieved context (`AzureOpenAI` client).

### 4. Persistence

*   **Frontend SQLite DB:** Stores user accounts, chat sessions, chat messages, and document metadata (filename, version, uploader).
*   **Backend `uploads/` Directory:** Stores the original uploaded document files.
*   **Backend `myindex/` Directory:** Stores the FAISS vector index (`index.faiss`, `index.pkl`) and basic metadata (`metadata.txt`).

## Data Flow

### Chat Query

1.  User sends message (Frontend UI).
2.  Frontend (`/send_message`) sends query text to Backend (`/query`).
3.  Backend embeds query, searches FAISS, returns relevant chunks.
4.  Frontend receives chunks, combines with original query into a prompt.
5.  Frontend sends prompt to Azure OpenAI Chat Completion API.
6.  Frontend receives generated response from Azure OpenAI.
7.  Frontend saves user message and assistant response to SQLite DB.
8.  Frontend displays response in UI.

### Document Upload (Admin)

1.  Admin uploads file (Frontend UI `/upload`).
2.  Frontend sends file + chunking params to Backend (`/upload`).
3.  Backend saves file to `uploads/`.
4.  Backend processes file (extracts text, chunks).
5.  Backend generates embeddings for chunks via Azure OpenAI Embeddings.
6.  Backend adds embeddings to FAISS index (`myindex/`) and updates metadata.
7.  Backend returns success to Frontend.
8.  Frontend saves document metadata (filename, version, uploader) to SQLite DB.
9.  Frontend displays success message.

## Technologies Used

*   **Programming Language:** Python
*   **Web Frameworks:** Flask (Frontend), FastAPI (Backend)
*   **Containerization:** Docker, Docker Compose
*   **Database:** SQLite (Frontend metadata)
*   **Vector Store:** FAISS
*   **AI/NLP:** LangChain, Azure OpenAI (Embeddings & Chat Completion)
*   **Frontend Libraries:** Jinja2 (Templating), Requests (HTTP client), Werkzeug (Security), Markdown/Markdown2
*   **Backend Libraries:** Uvicorn (ASGI Server), Pydantic (Data Validation) 