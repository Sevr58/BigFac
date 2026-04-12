from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    anthropic_api_key: str
    openai_api_key: str = ""
    tavily_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"  # "local" or "s3"
    storage_local_root: str = "/tmp/scf_uploads"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
