# loads .env file into environment variables

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    database_url_ro: str          # filled Day 4
    anthropic_api_key: str = ""  # filled Day 3
    rate_limit_requests: int = 10  # max /ask calls per client per window
    rate_limit_window_seconds: int = 60
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()