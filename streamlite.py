import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- Setup ---
HISTORY_DIR = "chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def save_chat_history(user_key, messages):
    filepath = os.path.join(HISTORY_DIR, f"{user_key}.json")
    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)

def load_chat_history(user_key):
    filepath = os.path.join(HISTORY_DIR, f"{user_key}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def main():
    import streamlit as st
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    USER_DB = {
        "admin": {"password": "admin123", "role": "admin"},
        "user": {"password": "user123", "role": "user"},
    }

    API_BASE_URL = "http://localhost:8000"

    st.set_page_config(page_title="🤖 AI Chat + Admin Panel", layout="centered")
    st.title("📄 AI Document Chatbot")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None

    user_key = st.session_state.username if st.session_state.logged_in else "guest"

    if "messages" not in st.session_state:
        st.session_state.messages = {}

    if user_key not in st.session_state.messages:
        st.session_state.messages[user_key] = load_chat_history(user_key)

    # --- Login ---
    if not st.session_state.logged_in:
        with st.expander("🔐 Login to access extra features"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                user = USER_DB.get(username)
                if user and user["password"] == password:
                    st.success(f"Welcome, {username}!")
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = user["role"]
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    # --- Logout ---
    if st.session_state.logged_in:
        st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.messages[user_key] = []
            save_chat_history(user_key, [])
            st.rerun()

    # --- Admin Upload Panel ---
    if st.session_state.get("role") == "admin":
        st.subheader("📤 Upload Document")
        with st.form("upload_form"):
            uploaded_file = st.file_uploader("Upload a PDF or TXT", type=["pdf", "txt"])
            chunk_size = st.number_input("Chunk Size", min_value=100, value=1000, step=100)
            chunk_overlap = st.number_input("Chunk Overlap", min_value=0, value=200, step=50)
            submit_button = st.form_submit_button("Upload and Index")

        if submit_button and uploaded_file:
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            data = {"chunk_size": str(chunk_size), "chunk_overlap": str(chunk_overlap)}
            with st.spinner("Uploading and indexing..."):
                response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
            if response.status_code == 201:
                res_json = response.json()
                st.success(f"✅ {res_json['message']}")
                st.write(f"Chunks created: {res_json['chunks_created']}")
            else:
                st.error(f"❌ {response.json()['detail']}")

        st.subheader("📊 Index Stats")
        stats = requests.get(f"{API_BASE_URL}/stats")
        if stats.status_code == 200:
            data = stats.json()
            st.metric("📁 Total Documents", data["total_documents"])
            st.metric("📑 Total Chunks", data["total_chunks"])
            st.caption(f"🕒 Last Updated: {data['last_updated']}")
        else:
            st.error("⚠️ Could not fetch stats")

    # --- Chat UI ---
    st.header("💬 Chat with AI")

    for msg in st.session_state.messages[user_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages[user_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = requests.post(f"{API_BASE_URL}/query", json={"query": prompt, "top_k": 3})
                if response.status_code == 200:
                    results = response.json()["results"]
                    context = "\n\n".join([res["content"] for res in results])
                    refined_prompt = f"Answer the user's question clearly and helpfully based on this context:\n\nContext:\n{context}\n\nQuestion: {prompt}"
                    gpt_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": refined_prompt}
                            ]
                        }
                    )
                    if gpt_response.status_code == 200:
                        final_answer = gpt_response.json()['choices'][0]['message']['content']
                    else:
                        final_answer = "Error calling GPT API"
                else:
                    final_answer = f"Error: {response.text}"

                st.markdown(final_answer)
                st.session_state.messages[user_key].append({"role": "assistant", "content": final_answer})
                save_chat_history(user_key, st.session_state.messages[user_key])

if __name__ == "__main__":
    main()