# TrainingTrack

A simple full-stack task manager for internship and student projects.

## Stack

- Python + Flask
- SQLite
- HTML + CSS + JavaScript

## Features

- Register / login / logout
- Private tasks per user
- Create, view, update and delete tasks
- Search, status, priority and category filters
- Simple statistics dashboard
- Responsive Kanban-style UI
- REST API backed by SQLite

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and create an account.

## API

Authenticated endpoints:

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/<id>`
- `PUT /api/tasks/<id>`
- `DELETE /api/tasks/<id>`
- `GET /api/stats`
- `GET /health`

## Notes

This is a small 4-week training project, so authentication is intentionally session-based and the application stays focused on core web-development concepts.
