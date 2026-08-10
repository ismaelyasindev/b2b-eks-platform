"""Connection storm load generator.

Targets the Auth service signup path and injects the SRE chaos header so each
request forces a `SELECT pg_sleep(5)` on the backend, saturating the DB
connection pool and surfacing connection-tracking / saturation alerts.

Run against the local gateway:
    locust -f load-tests/locustfile.py --host http://localhost:8080
"""

from locust import HttpUser, between, task


class NewUserStorm(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def signup_storm(self):
        """
        Executes an intensive connection traffic storm targeting the internal
        Auth service. Injects the 'X-Trigger-Storm' header to force connection
        tracking alerts.
        """
        self.client.post(
            "/api/auth/signup",
            json={"email": "test-load@platform.local"},
            headers={"X-Trigger-Storm": "true"},
        )
