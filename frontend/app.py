from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import requests
from datetime import datetime

# --- App Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
db.metadata.clear()
# --- Models ---

# --- Environment ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE_URL = "http://localhost:8000"

# --- Helper Functions ---
def get_current_user():
    if "username" in session:
        return User.query.filter_by(username=session["username"]).first()
    return None

def save_message(user, role, content, session_id):
    message = ChatMessage(user_id=user.id, role=role, content=content, session_id=session_id)
    db.session.add(message)
    db.session.commit()

def get_user_messages(user):
    return ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.timestamp.asc()).all()

# --- Routes ---
def create_tables():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship("ChatMessage", backref="session", lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["username"] = user.username
            session["theme"] = session.get("theme", "light")
            return redirect(url_for("chat"))
        else:
            error = "Invalid credentials"

    return render_template("login.html", error=error, theme=session.get("theme", "light"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists")
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/toggle-theme")
def toggle_theme():
    session["theme"] = "dark" if session.get("theme") == "light" else "light"
    return redirect(request.referrer or url_for("chat"))

@app.route("/chat", methods=["GET"])
def chat():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    # Load or create current session
    session_id = request.args.get("session_id")
    if not session_id:
        chat_session = ChatSession(user_id=user.id)
        db.session.add(chat_session)
        db.session.commit()
        return redirect(url_for("chat", session_id=chat_session.id))
    else:
        chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if not chat_session:
            return redirect(url_for("chat"))

    messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.timestamp).all()
    sessions = ChatSession.query.filter_by(user_id=user.id).order_by(ChatSession.created_at.desc()).all()

    return render_template("chat.html",
                           messages=messages,
                           sessions=sessions,
                           current_session=chat_session,
                           username=user.username,
                           role="admin" if user.is_admin else "user",
                           theme=session.get("theme", "light"))

@app.route("/send_message", methods=["POST"])
def send_message():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get("prompt", "")
    session_id = data.get("session_id")

    if not prompt or not session_id:
        return jsonify({"error": "Missing prompt or session ID"}), 400

    # Save user message
    chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not chat_session:
        return jsonify({"error": "Invalid session"}), 404

    save_message(user, "user", prompt, session_id)

    # Process message (OpenAI + FastAPI)
    response = requests.post(f"{API_BASE_URL}/query", json={"query": prompt, "top_k": 3})
    results = response.json()["results"]
    context = "\n\n".join([r["content"] for r in results])
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

    answer = gpt_response.json()["choices"][0]["message"]["content"]
    save_message(user, "assistant", answer, session_id)

    return jsonify({"response": answer})

@app.route("/upload", methods=["GET", "POST"])
def upload():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for("chat"))

    message = None
    if request.method == "POST":
        file = request.files["file"]
        chunk_size = request.form.get("chunk_size", 1000)
        chunk_overlap = request.form.get("chunk_overlap", 200)

        if file:
            files = {"file": (file.filename, file.stream, file.content_type)}
            data = {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
            res = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
            message = res.json().get("message") if res.status_code == 201 else res.json().get("detail")

    return render_template("upload.html", username=user.username, message=message, theme=session.get("theme", "light"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True, port=5000)

