from locust import HttpUser, between, task


class NewUserStorm(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def signup_storm(self):
        self.client.post(
            "/auth/signup",
            json={"email": "test@test.com"},
            headers={"X-Trigger-Storm": "true"},
        )
