# loads .env file into environment variables

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    database_url_ro: str          # filled Day 4
    anthropic_api_key: str = ""  # filled Day 3
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()