from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str
    database_url: str
    jwt_secret: str
    usd_to_inr: float = 96.0

    class Config:
        env_file = ".env"

settings = Settings()
