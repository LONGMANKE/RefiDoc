# 🧠 Refidoc AI Assistant

<p align="center">
  <img src="frontend/static/refidoc-logo.png" alt="RefiDoc Logo" width="250">
</p>

Refidoc is an intelligent document assistant that allows users to upload PDF/TXT files, index them using vector embeddings (FAISS + LangChain), and chat with an AI agent that answers based on document content.

---

## 📁 Project Structure

```
AIAGENTTEST/
├── backend/
│   ├── main.py           # FastAPI backend
│   ├── myindex/          # FAISS index
│   ├── uploads/          # Uploaded documents
│   └── utils/            # Document loader utilities
├── frontend/
│   ├── app.py            # Flask frontend
│   ├── static/           # Logo, styles
│   ├── templates/        # HTML templates
│   └── instance/chat_app.db # SQLite DB
├── .env                  # Secrets (OpenAI key, etc.)
├── .gitignore
├── README.md             # You're here!
├── requirements.txt
```

---

## ⚙️ Setup

1. **Clone repository**

   ```bash
   git clone https://github.com/yourname/refidoc.git
   cd refidoc
   ```

2. **Create virtualenv and install dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_key
   SECRET_KEY=your_flask_secret
   ```

---

## 🚀 Running the Application

### Backend (FastAPI)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend (Flask)

```bash
cd frontend
python app.py
```

---

## 🔐 Admin Credentials

Default login:

- Username: `admin`
- Password: `admin123`

---

## 📁 Document Upload & Chat

- Admin can upload `.pdf` or `.txt` files.
- Files are chunked and indexed using LangChain + FAISS.
- Users can ask questions, and the app responds contextually.

---

## 📊 Admin Panel

Admin can:

- Upload & manage documents
- View and delete users
- See stats: total docs, chunks, last updated

---

## 🧩 Use Case: Tailored for Organizations with Agents & Call Centers

RefiDoc is especially useful for:

### 🎧 Call Centers & Support Teams

> Empower your customer service agents with instant answers from internal documents.

✅ **Use RefiDoc to:**

- Upload policy documents, product manuals, or FAQs
- Enable agents to **chat with documents** in real-time while assisting clients
- Reduce response time and improve first-call resolution
- Support **multilingual teams** with centralized knowledge

### 🏢 Internal Teams & Enterprises

> RefiDoc becomes your **smart internal documentation assistant**.

✅ Ideal for:

- HR teams referencing policies
- Legal teams querying contracts
- IT teams managing technical documentation
- Finance departments retrieving invoice or tax information

💡 Whether you’re running a small support desk or managing enterprise knowledge, **RefiDoc offers fast, AI-driven document querying** to improve productivity and accuracy.
