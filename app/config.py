import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bulk Certificate Generator API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./certificates.db"
    
    # Media Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MEDIA_DIR: Path = BASE_DIR / "media" / "certificates"
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()

# Ensure media directory exists
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
