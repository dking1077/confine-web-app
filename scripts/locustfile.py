from locust import HttpUser, task, between
import random


class ConfineUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login once per user and store the access token."""
        payload = {
            "email": "test@example.com",      # change to a real test user
            "password": "password123"
        }
        with self.client.post("/auth/login", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = None
                self.headers = {}
                resp.failure(f"Login failed: {resp.status_code}")

    @task(5)
    def search(self):
        """Main search flow – highest weight."""
        if not self.token:
            return

        queries = [
            "drake god's plan",
            "the weeknd blinding lights",
            "taylor swift anti hero",
            "kendrick lamar",
            "billie eilish bad guy",
            "adele easy on me",
            "post malone circles",
            "dua lipa levitating",
        ]
        query = random.choice(queries)

        with self.client.post(
            "/search/",
            json={"search_input": query},
            headers=self.headers,
            name="/search/",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202):
                resp.success()
            else:
                resp.failure(f"Search failed: {resp.status_code}")

    @task(1)
    def session_status(self):
        """Light authenticated endpoint."""
        if not self.token:
            return

        self.client.get(
            "/auth/session-status",
            headers=self.headers,
            name="/auth/session-status",
        )