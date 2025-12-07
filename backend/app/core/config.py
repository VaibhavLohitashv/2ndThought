from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    GOOGLE_APPLICATION_CREDENTIALS: str
    FIREBASE_PROJECT_ID: str
    # optional Redis URL (may be absent in single-process setups)
    REDIS_URL: str | None = None
    # Base URL for API (used for generating absolute image URLs)
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
