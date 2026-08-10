"""Shared base settings parsing.

Each microservice imports `settings` for cross-cutting concerns (JWT signing,
AWS/SQS routing, inter-service URLs). Database credentials are intentionally
NOT modelled here — they are resolved dynamically in `shared.db` so that no
plaintext secret is ever serialized onto disk.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "local"

    # --- Auth / JWT (HS256 shared secret across the trust boundary) ---
    JWT_SECRET_KEY: str = "local_development_only_secret_key_987654321"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # --- AWS / SQS ---
    AWS_DEFAULT_REGION: str = "eu-west-2"
    AWS_ENDPOINT_URL: str | None = None
    SQS_QUEUE_NAME: str = "order-completed"

    # --- Inter-service synchronous calls ---
    # In EKS this resolves to the internal cluster service DNS; docker-compose
    # overrides it to the local container hostname.
    PRODUCT_SERVICE_URL: str = "http://product-svc.prod.svc.cluster.local"
    PRODUCT_STOCK_TIMEOUT_SECONDS: float = 2.0


settings = Settings()
