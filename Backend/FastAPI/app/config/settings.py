# app/config.py
"""
Configuration settings for the application.
"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Settings class to store configuration variables.
    """

    API_KEY: str = os.getenv("API_KEY", "secret")
    POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY")
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "Blockhouse-FastAPI")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET: str = os.getenv("AWS_STORAGE_BUCKET")
    AWS_REGION: str = os.getenv("AWS_REGION")
    DOCS_USERNAME: str = os.getenv("DOCS_USERNAME", "admin")
    DOCS_PASSWORD: str = os.getenv("DOCS_PASSWORD", "admin123")
    DD_API_KEY: str = os.getenv("DD_API_KEY")
    DD_LOGGING_ENV: str = os.getenv("DD_LOGGING_ENV", "development")
    DD_SERVICE: str = os.getenv("DD_SERVICE", "fastapi-app")
    DD_HOSTNAME: str = os.getenv("DD_HOSTNAME", "localhost")


settings = Settings()

