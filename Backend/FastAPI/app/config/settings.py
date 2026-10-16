# app/config.py
"""
Configuration settings for the application.
"""

from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Settings class to store configuration variables.
    """

    # BaseSettings reads each field from the environment itself (after load_dotenv above);
    # an empty variable, such as an unset GitHub secret, falls back to the default.
    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    API_KEY: str = "secret"
    POLYGON_API_KEY: Optional[str] = None
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "Blockhouse-FastAPI"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_STORAGE_BUCKET: Optional[str] = None
    AWS_REGION: Optional[str] = None
    DOCS_USERNAME: str = "admin"
    DOCS_PASSWORD: str = "admin123"
    DD_API_KEY: Optional[str] = None
    DD_LOGGING_ENV: str = "development"
    DD_SERVICE: str = "fastapi-app"
    DD_HOSTNAME: str = "localhost"


settings = Settings()

