from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta
from openai import AzureOpenAI
from werkzeug.utils import secure_filename


# --- App Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat_app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
db.metadata.clear()

# ✅ Upload folder
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/uploads'))
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Environment ---
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
API_BASE_URL = os.getenv("FASTAPI_BACKEND", "http://localhost:8000")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    first_prompt = db.Column(db.String(255))
    messages = db.relationship("ChatMessage", backref="session", lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    version = db.Column(db.Integer, default=1)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    uploader = db.relationship("User", backref="uploaded_documents")

# --- Helpers ---
def get_current_user():
    if "username" in session:
        return User.query.filter_by(username=session["username"]).first()
    return None

def save_message(user, role, content, session_id):
    message = ChatMessage(user_id=user.id, role=role, content=content, session_id=session_id)
    db.session.add(message)
    db.session.commit()

# --- Routes ---
@app.route("/send_message", methods=["POST"])
def send_message():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get("prompt")
    session_id = data.get("session_id")

    if not prompt or not session_id:
        return jsonify({"error": "Missing prompt or session ID"}), 400

    chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not chat_session:
        return jsonify({"error": "Invalid session"}), 404

    if not chat_session.first_prompt:
        chat_session.first_prompt = prompt[:255]
        db.session.commit()

    save_message(user, "user", prompt, session_id)

    response = requests.post(f"{API_BASE_URL}/query", json={"query": prompt, "top_k": 3})
    results = response.json()["results"]
    context = "\n\n".join([r["content"] for r in results])

    refined_prompt = f"Answer the user's question clearly based on this context:\n\nContext:\n{context}\n\nQuestion: {prompt}"

    gpt_response = client.chat.completions.create(
        model=AZURE_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": refined_prompt},
        ]
    )

    answer = gpt_response.choices[0].message.content
    save_message(user, "assistant", answer, session_id)

    return jsonify({"response": answer})

# --- Routes ---
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
        error = "Invalid credentials"
    return render_template("login.html", error=error, theme=session.get("theme", "light"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists")
        hashed = generate_password_hash(password)
        user = User(username=username, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
# --- Routes ---
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/toggle-theme")
def toggle_theme():
    session["theme"] = "dark" if session.get("theme") == "light" else "light"
    return redirect(request.referrer or url_for("chat"))

@app.route("/chat", methods=["GET"])
def chat():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    session_id = request.args.get("session_id")
    if not session_id:
        chat_session = ChatSession(user_id=user.id)
        db.session.add(chat_session)
        db.session.commit()
        return redirect(url_for("chat", session_id=chat_session.id))

    chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not chat_session:
        return redirect(url_for("chat"))

    messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.timestamp).all()
    sessions = ChatSession.query.filter_by(user_id=user.id).order_by(ChatSession.created_at.desc()).all()

    return render_template(
        "chat.html",
        messages=messages,
        sessions=sessions,
        current_session=chat_session,
        username=user.username,
        role="admin" if user.is_admin else "user",
        theme=session.get("theme", "light"),
        current_time=datetime.now(),
        timedelta=timedelta  # 👈 This line fixes your error!
    )

# --- Upload with Versioning ---
@app.route("/upload", methods=["GET", "POST"])
def upload():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for("chat"))

    message = None
    stats = {"total_documents": "?", "total_chunks": "?", "last_updated": "?"}

    try:
        stats_response = requests.get(f"{API_BASE_URL}/stats")
        if stats_response.ok:
            stats = stats_response.json()
    except Exception as e:
        print("Error fetching stats:", e)

    if request.method == "POST":
        file = request.files.get("file")
        chunk_size = request.form.get("chunk_size", 1000)
        chunk_overlap = request.form.get("chunk_overlap", 200)

        if file:
            try:
                original_name = secure_filename(file.filename)
                base_name, ext = os.path.splitext(original_name)

                # Get current highest version
                existing_versions = Document.query.filter(Document.filename.like(f"{base_name}_v%{ext}")).all()
                version = 1 + max([doc.version for doc in existing_versions], default=0)
                versioned_name = f"{base_name}_v{version}{ext}"
                file.filename = versioned_name

                # Send to FastAPI backend for chunking/indexing
                files = {"file": (file.filename, file.stream, file.content_type)}
                data = {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
                res = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)

                if res.status_code == 201:
                    # Save file locally (optional)
                    file.stream.seek(0)
                    local_path = os.path.join(app.config["UPLOAD_FOLDER"], versioned_name)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    file.save(local_path)

                    # Save to database
                    doc = Document(filename=versioned_name, version=version, uploader_id=user.id)
                    db.session.add(doc)
                    db.session.commit()

                    message = f"Uploaded and indexed as {versioned_name}"
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return jsonify({"message": message})
                    stats = requests.get(f"{API_BASE_URL}/stats").json()
                else:
                    message = res.json().get("detail", "Upload to backend failed.")
            except Exception as e:
                message = f"Upload failed: {str(e)}"
        else:
            message = "Please select a file."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"message": message})

    return render_template(
        "upload.html",
        username=user.username,
        message=message,
        stats=stats,
        theme=session.get("theme", "light")
    )
    
# --- View Documents with Versions ---
@app.route("/documents")
def documents():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for("chat"))

    all_docs = Document.query.order_by(Document.filename, Document.version.desc()).all()
    grouped = {}
    for doc in all_docs:
        base = doc.filename.rsplit("_v", 1)[0]
        grouped.setdefault(base, []).append(doc)

    return render_template("documents.html", grouped=grouped, username=user.username, theme=session.get("theme", "light"))

# --- Delete Version ---
@app.route("/delete_file/<int:doc_id>", methods=["POST"])
def delete_file(doc_id):
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for("chat"))

    doc = Document.query.get(doc_id)
    if doc:
        # delete physical file
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], doc.filename))
        except FileNotFoundError:
            pass

        # delete from DB
        db.session.delete(doc)
        db.session.commit()

    return redirect(url_for("documents"))

@app.route("/users", methods=["GET"])
def manage_users():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for("chat"))

    users = User.query.order_by(User.id).all()
    return render_template("users.html", users=users, username=user.username, theme=session.get("theme", "light"))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    current_user = get_current_user()
    if not current_user or not current_user.is_admin:
        return redirect(url_for("chat"))

    user_to_delete = User.query.get(user_id)
    if user_to_delete and user_to_delete.username != current_user.username:
        ChatMessage.query.filter_by(user_id=user_id).delete()
        ChatSession.query.filter_by(user_id=user_id).delete()
        db.session.delete(user_to_delete)
        db.session.commit()

    return redirect(url_for("manage_users"))
@app.route("/delete_chat/<int:chat_id>", methods=["POST"])
def delete_chat(chat_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    session_to_delete = ChatSession.query.filter_by(id=chat_id, user_id=user.id).first()
    if session_to_delete:
        ChatMessage.query.filter_by(session_id=session_to_delete.id).delete()
        db.session.delete(session_to_delete)
        db.session.commit()

    # Redirect to most recent session or create new
    remaining = ChatSession.query.filter_by(user_id=user.id).order_by(ChatSession.created_at.desc()).first()
    if remaining:
        return redirect(url_for("chat", session_id=remaining.id))
    else:
        # No sessions left, create one
        new_session = ChatSession(user_id=user.id)
        db.session.add(new_session)
        db.session.commit()
        return redirect(url_for("chat", session_id=new_session.id))

# --- Entry Point ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password_hash=generate_password_hash("admin123"), is_admin=True)
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True, port=5000)
