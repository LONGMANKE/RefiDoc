
# 🧠 RefiDoc AI Assistant (Powered by Azure OpenAI)

<p align="center">
  <img src="frontend/static/refidoc-logo.png" alt="RefiDoc Logo" width="250">
</p>

RefiDoc is a secure, intelligent document assistant powered by **Azure OpenAI**, enabling users to upload PDF/TXT files, index them using **FAISS + LangChain**, and chat with an AI agent that answers based on internal document context.

---

## 📁 Project Structure

```
AIAGENTTEST/
├── backend/
│   ├── main.py           # FastAPI backend (embedding + vector search)
│   ├── myindex/          # FAISS index
│   ├── uploads/          # Uploaded documents
│   └── utils/            # Document loader utilities
├── frontend/
│   ├── app.py            # Flask frontend (chat UI)
│   ├── static/           # Logo, styles
│   ├── templates/        # HTML templates
│   └── instance/chat_app.db # SQLite DB
├── .env                  # Environment variables (Azure secrets)
├── .gitignore
├── README.md             # You're here!
├── requirements.txt
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/longmanke/refidoc.git
cd refidoc
```

### 2. Create a Virtual Environment & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Configure Azure Environment Variables

Create a `.env` file at the project root:

```
SECRET_KEY=your_flask_secret

# Azure OpenAI Chat (used by Flask frontend)
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_DEPLOYMENT_NAME=your_chat_model_deployment  # e.g. gpt-4
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Azure OpenAI Embeddings (used by FastAPI backend)
AZURE_EMBEDDING_DEPLOYMENT=your_embedding_deployment  # e.g. text-embedding-3-large

# FastAPI backend
FASTAPI_BACKEND=http://localhost:8000
```

✅ **Important:** Add `.env` to `.gitignore` so secrets are not pushed.

---

## 🚀 Running the Application

### Start Backend (FastAPI for Document Indexing)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Start Frontend (Flask Chat App)

```bash
cd frontend
python app.py
```

---

## 🔐 Admin Access

Default login credentials:

- **Username**: `admin`
- **Password**: `admin123`

---

## 💬 Features

- Upload `.pdf` or `.txt` files
- Index documents using **LangChain + FAISS**
- Query document content using **Azure OpenAI chat completions**
- Chat history saved per user/session
- Toggle between light/dark mode
- Admin dashboard for managing documents & users

---

## 📊 Admin Panel

Admins can:

- ✅ Upload and manage documents
- 👥 View/delete users
- 📈 View document stats (chunks, last updated)

---

## 🎯 Use Case: Ideal for Call Centers & Internal Knowledge Bases

### ☎️ For Call Centers

Empower agents with instant access to policy documents, manuals, FAQs—without leaving the screen.

- Answer client queries quickly
- Improve customer satisfaction
- Enable multilingual support

### 🏢 For Internal Teams

Let your staff chat with documentation:

- HR: policy documents  
- Legal: contracts  
- Finance: tax and compliance files  
- IT: technical documentation

---

## ☁️ Setting Up Azure OpenAI

### 1. Prerequisites

- Azure account: https://azure.com
- Azure OpenAI access (apply at [https://aka.ms/oai/access](https://aka.ms/oai/access))

### 2. Create Azure OpenAI Resource

1. Go to Azure Portal > Create Resource > "Azure OpenAI"
2. Choose location (e.g., East US), create resource

### 3. Deploy Chat Model

Go to "Deployments" > + Create

- Model: `gpt-35-turbo` or `gpt-4`
- Deployment name: `gpt-35-refidoc` or similar

### 4. Deploy Embedding Model

- Model: `text-embedding-3-large`
- Deployment name: `text-embedding-3-large`

### 5. Get Keys and Endpoint

- Navigate to Keys & Endpoint section of your Azure OpenAI resource
- Copy: `Key`, `Endpoint`

### 6. Update `.env`

See earlier section for template. Use actual values from portal.

---
