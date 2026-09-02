from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("TRAININGTRACK_DB", BASE_DIR / "trainingtrack.db"))

ALLOWED_STATUS = {"Pending", "In Progress", "Completed"}
ALLOWED_PRIORITY = {"High", "Medium", "Low"}
ALLOWED_CATEGORIES = {"Frontend", "Backend", "JavaScript", "Testing", "Documentation", "Other"}
MAX_TITLE_LENGTH = 80
MAX_CATEGORY_LENGTH = 40
MAX_NOTES_LENGTH = 500

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "trainingtrack-dev-secret-change-me"),
    MAX_CONTENT_LENGTH=64 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
)


def get_db() -> sqlite3.Connection:
    """Open one SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception: BaseException | None = None) -> None:
    """Close the request database connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create the user and task tables when the app starts."""
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            priority TEXT NOT NULL DEFAULT 'Medium',
            due_date TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
        """
    )
    db.commit()


def current_user() -> sqlite3.Row | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def require_user():
    user = current_user()
    if user is None:
        return None
    return user


def seed_user_tasks(user_id: int) -> None:
    """Create a few starter tasks for a new workspace."""
    db = get_db()
    starter_tasks = [
        (
            user_id,
            "Build responsive landing page",
            "Frontend",
            "Completed",
            "High",
            "2026-09-01",
            "Used semantic HTML and responsive CSS.",
        ),
        (
            user_id,
            "Connect task REST endpoints",
            "Backend",
            "Completed",
            "High",
            "2026-09-02",
            "Implemented GET, POST, PUT and DELETE routes.",
        ),
        (
            user_id,
            "Add task filtering",
            "JavaScript",
            "In Progress",
            "Medium",
            "2026-09-03",
            "Filter by status and category without page reload.",
        ),
        (
            user_id,
            "Prepare project documentation",
            "Documentation",
            "Pending",
            "Low",
            "2026-09-05",
            "Prepare report, synopsis and viva notes.",
        ),
    ]
    db.executemany(
        """
        INSERT INTO tasks
            (user_id, title, category, status, priority, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        starter_tasks,
    )
    db.commit()


def validate_registration(name: str, email: str, password: str) -> str | None:
    if not name or not email or not password:
        return "All fields are required."
    if len(name) > 60:
        return "Name must be 60 characters or fewer."
    if "@" not in email or len(email) > 120:
        return "Enter a valid email address."
    if len(password) < 6:
        return "Password must be at least 6 characters."
    return None


def validate_task_payload(data: dict[str, Any], partial: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    fields = {"title", "category", "status", "priority", "due_date", "notes"}
    unknown = set(data) - fields
    if unknown:
        return None, f"Unsupported field(s): {', '.join(sorted(unknown))}"

    if not partial:
        if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
            return None, "title is required"
        if not isinstance(data.get("category"), str) or not data.get("category", "").strip():
            return None, "category is required"

    clean: dict[str, Any] = {}

    if "title" in data:
        if not isinstance(data["title"], str):
            return None, "title must be a string"
        value = data["title"].strip()
        if not value:
            return None, "title cannot be empty"
        if len(value) > MAX_TITLE_LENGTH:
            return None, f"title must be {MAX_TITLE_LENGTH} characters or fewer"
        clean["title"] = value

    if "category" in data:
        if not isinstance(data["category"], str):
            return None, "category must be a string"
        value = data["category"].strip()
        if value not in ALLOWED_CATEGORIES:
            return None, f"category must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        clean["category"] = value

    if "status" in data:
        if data["status"] not in ALLOWED_STATUS:
            return None, f"status must be one of: {', '.join(sorted(ALLOWED_STATUS))}"
        clean["status"] = data["status"]

    if "priority" in data:
        if data["priority"] not in ALLOWED_PRIORITY:
            return None, f"priority must be one of: {', '.join(sorted(ALLOWED_PRIORITY))}"
        clean["priority"] = data["priority"]

    if "due_date" in data:
        value = data["due_date"] or ""
        if value:
            if not isinstance(value, str):
                return None, "due_date must use YYYY-MM-DD format"
            try:
                date.fromisoformat(value)
            except ValueError:
                return None, "due_date must use YYYY-MM-DD format"
        clean["due_date"] = value

    if "notes" in data:
        if not isinstance(data["notes"], str):
            return None, "notes must be a string"
        value = data["notes"].strip()
        if len(value) > MAX_NOTES_LENGTH:
            return None, f"notes must be {MAX_NOTES_LENGTH} characters or fewer"
        clean["notes"] = value

    return clean, None


def row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    task = dict(row)
    task["is_overdue"] = bool(task["due_date"]) and task["due_date"] < date.today().isoformat() and task["status"] != "Completed"
    return task


def user_task(task_id: int, user_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()


@app.get("/")
def index():
    user = require_user()
    if user is None:
        return redirect(url_for("login"))
    return render_template("index.html", user=user)


@app.get("/login")
def login():
    if require_user() is not None:
        return redirect(url_for("index"))
    return render_template("login.html")


@app.post("/login")
def login_post():
    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", ""))
    user = get_db().execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password."), 401

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("index"))


@app.get("/register")
def register():
    if require_user() is not None:
        return redirect(url_for("index"))
    return render_template("register.html")


@app.post("/register")
def register_post():
    name = str(request.form.get("name", "")).strip()
    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", ""))
    error = validate_registration(name, email, password)
    if error:
        return render_template("register.html", error=error, name=name, email=email), 400

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that email already exists.",
            name=name,
            email=email,
        ), 409

    seed_user_tasks(cursor.lastrowid)
    session.clear()
    session["user_id"] = cursor.lastrowid
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/tasks")
def get_tasks():
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    db = get_db()
    rows = db.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC", (user["id"],)
    ).fetchall()
    tasks = [row_to_task(row) for row in rows]

    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "All")
    priority = request.args.get("priority", "All")
    category = request.args.get("category", "All")

    if q:
        tasks = [t for t in tasks if q in f"{t['title']} {t['category']} {t['notes']}".lower()]
    if status != "All":
        tasks = [t for t in tasks if t["status"] == status]
    if priority != "All":
        tasks = [t for t in tasks if t["priority"] == priority]
    if category != "All":
        tasks = [t for t in tasks if t["category"] == category]

    return jsonify(tasks)


@app.post("/api/tasks")
def create_task():
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object expected"}), 400
    payload, error = validate_task_payload(data)
    if error:
        return jsonify({"error": error}), 400

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO tasks (user_id, title, category, status, priority, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            payload["title"],
            payload["category"],
            payload.get("status", "Pending"),
            payload.get("priority", "Medium"),
            payload.get("due_date", ""),
            payload.get("notes", ""),
        ),
    )
    db.commit()
    row = user_task(cursor.lastrowid, user["id"])
    return jsonify(row_to_task(row)), 201


@app.get("/api/tasks/<int:task_id>")
def get_task(task_id: int):
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401
    row = user_task(task_id, user["id"])
    if row is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(row_to_task(row))


@app.put("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object expected"}), 400
    payload, error = validate_task_payload(data, partial=True)
    if error:
        return jsonify({"error": error}), 400
    if not payload:
        return jsonify({"error": "no editable fields supplied"}), 400

    if user_task(task_id, user["id"]) is None:
        return jsonify({"error": "task not found"}), 404

    db = get_db()
    assignments = ", ".join(f"{field} = ?" for field in payload)
    values = [payload[field] for field in payload] + [task_id, user["id"]]
    db.execute(f"UPDATE tasks SET {assignments} WHERE id = ? AND user_id = ?", values)
    db.commit()
    return jsonify(row_to_task(user_task(task_id, user["id"])))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    db = get_db()
    cursor = db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user["id"])
    )
    if cursor.rowcount == 0:
        return jsonify({"error": "task not found"}), 404
    db.commit()
    return jsonify({"message": "task deleted", "id": task_id})


@app.get("/api/stats")
def get_stats():
    user = require_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    db = get_db()
    user_id = user["id"]
    total = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)).fetchone()[0]
    completed = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()[0]
    progress = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'In Progress'", (user_id,)).fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Pending'", (user_id,)).fetchone()[0]
    overdue = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date <> '' AND due_date < ? AND status <> 'Completed'",
        (user_id, date.today().isoformat()),
    ).fetchone()[0]
    categories = db.execute(
        "SELECT category, COUNT(*) AS count FROM tasks WHERE user_id = ? GROUP BY category ORDER BY count DESC",
        (user_id,),
    ).fetchall()

    return jsonify(
        {
            "total": total,
            "completed": completed,
            "in_progress": progress,
            "pending": pending,
            "overdue": overdue,
            "categories": [dict(row) for row in categories],
        }
    )


@app.get("/health")
def health():
    get_db().execute("SELECT 1").fetchone()
    return jsonify({"status": "ok", "service": "trainingtrack"})


@app.errorhandler(413)
def request_too_large(error):
    return jsonify({"error": "request body is too large"}), 413


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
