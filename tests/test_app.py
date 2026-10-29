"""Regression tests for TrainingTrack's Flask API."""

import os
import tempfile
import unittest
from pathlib import Path

_TEST_DIR = tempfile.TemporaryDirectory()
os.environ["TRAININGTRACK_DB"] = str(Path(_TEST_DIR.name) / "test_trainingtrack.db")
os.environ["SECRET_KEY"] = "test-only-secret-key"

from app import app, get_db  # noqa: E402


class TrainingTrackTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-only-secret-key")
        self.client = app.test_client()
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM tasks")
            db.execute("DELETE FROM users")
            db.commit()
        response = self.client.post(
            "/register",
            data={"name": "Test User", "email": "test@example.com", "password": "correct-horse"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_api_requires_authentication(self):
        response = app.test_client().get("/api/tasks")
        self.assertEqual(response.status_code, 401)

    def test_create_task_with_other_category(self):
        response = self.client.post(
            "/api/tasks",
            json={
                "title": "Regression test",
                "category": "Other",
                "priority": "Medium",
                "status": "Pending",
                "notes": "Created by automated test",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["category"], "Other")

    def test_unknown_category_is_rejected(self):
        response = self.client.post(
            "/api/tasks",
            json={"title": "Unsupported category", "category": "Performance"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("category must be one of", response.get_json()["error"])

    def test_user_cannot_access_another_users_task(self):
        first_task = self.client.get("/api/tasks").get_json()[0]
        second_client = app.test_client()
        response = second_client.post(
            "/register",
            data={"name": "Second User", "email": "second@example.com", "password": "correct-horse"},
        )
        self.assertEqual(response.status_code, 302)
        response = second_client.get(f"/api/tasks/{first_task['id']}")
        self.assertEqual(response.status_code, 404)

    def test_stats_match_task_counts(self):
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.get_json()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["completed"] + stats["in_progress"] + stats["pending"], stats["total"])


if __name__ == "__main__":
    unittest.main()
