# TrainingTrack

**A focused task-management workspace for students, interns, and small project teams.**

TrainingTrack helps users organize work in a Kanban board, manage deadlines, and review progress from a live statistics dashboard. It is built with Flask, SQLite, vanilla JavaScript, HTML, and CSS.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![Database](https://img.shields.io/badge/Database-SQLite-003B57)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Account management:** register, sign in, and sign out with password hashing.
- **Private task data:** task queries are scoped to the authenticated user.
- **Kanban workflow:** organize tasks as Pending, In Progress, or Completed.
- **Task management:** create, edit, and delete tasks with due dates, notes, categories, and priority.
- **Search and filters:** narrow tasks by text, status, priority, and category.
- **Sorting:** order tasks by creation, priority, or due date.
- **Progress dashboard:** review task counts, overdue work, and completion rate.
- **Responsive UI:** mobile-friendly layout with light and dark themes.
- **JSON API:** CRUD endpoints, statistics, and a health check.
- **Regression checks:** automated tests run through GitHub Actions.

## Technology

| Layer | Technology |
| --- | --- |
| Server | Python, Flask |
| Data | SQLite with parameterized SQL queries |
| Authentication | Flask sessions, Werkzeug password hashing |
| Frontend | HTML, CSS, vanilla JavaScript |
| Testing | Python `unittest`, Flask test client |
| CI | GitHub Actions |

## Run locally

### 1. Requirements

- Python 3.10 or newer
- Git

### 2. Clone and install

```bash
git clone https://github.com/purigauravkumar/TrainingTrack.git
cd TrainingTrack
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the application

Set a unique secret key before running the app. Keep it private and do not commit it to Git.

**Windows PowerShell**
```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
python app.py
```

**macOS / Linux**
```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and create an account. The SQLite database is created automatically on first start.

Optional configuration:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Flask session signing key | Development fallback in `app.py`; set explicitly for any deployment |
| `PORT` | Local server port | `5000` |
| `FLASK_DEBUG` | Enable Flask debug mode | `0` |
| `COOKIE_SECURE` | Mark session cookie as HTTPS-only | `0` |
| `TRAININGTRACK_DB` | Database file path | `trainingtrack.db` in the project directory |

## API reference

All task and statistics endpoints require an authenticated session. Responses are JSON.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/tasks` | List tasks; supports `q`, `status`, `priority`, and `category` query parameters |
| `POST` | `/api/tasks` | Create a task |
| `GET` | `/api/tasks/<id>` | Retrieve one task |
| `PUT` | `/api/tasks/<id>` | Update supplied task fields |
| `DELETE` | `/api/tasks/<id>` | Delete a task |
| `GET` | `/api/stats` | Retrieve task counts and category totals |
| `GET` | `/health` | Check that the application and database respond |

Example create-task request:

```json
{
  "title": "Write project documentation",
  "category": "Documentation",
  "status": "In Progress",
  "priority": "Medium",
  "due_date": "2026-11-15",
  "notes": "Document setup and API usage."
}
```

Supported categories: `Frontend`, `Backend`, `JavaScript`, `Testing`, `Documentation`, and `Other`.

## Run tests

```bash
python -m unittest discover -s tests -v
```

The test suite covers health checks, authentication requirements, task creation and category validation, per-user task isolation, and dashboard statistics. GitHub Actions runs the regression suite for pushes to the main branch and pull requests.

## Project structure

```text
TrainingTrack/
├── app.py                 # Flask routes, validation, and SQLite access
├── reset_db.py            # Local database reset utility
├── requirements.txt       # Python dependencies
├── templates/
│   ├── index.html         # Task board and task modal
│   ├── login.html         # Sign-in page
│   └── register.html      # Registration page
├── static/
│   ├── css/style.css      # Responsive themes and layout
│   └── js/app.js          # UI rendering and API calls
├── tests/
│   └── test_app.py        # API regression tests
└── .github/workflows/
    └── tests.yml          # Automated test workflow
```

## Security and deployment notes

- Passwords are stored as hashes, not plaintext.
- SQL queries use parameters, and task reads/updates/deletes are scoped to the signed-in user.
- Set a strong, private `SECRET_KEY` for deployments and enable `COOKIE_SECURE=1` when serving over HTTPS.
- Use a production WSGI server and HTTPS for deployment; Flask's built-in server is intended for local development.
- This is a learning project. Before public production use, add CSRF protection for form/session-authenticated state changes, rate limiting for authentication endpoints, and a deployment-specific configuration review.

## License

MIT — see [LICENSE](LICENSE).
