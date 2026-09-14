from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TheOwlHouse"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    host: str = "0.0.0.0"
    port: int = 8000
    admin_username: str = "admin"
    admin_password: str = "admin123"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{DB_PATH.as_posix()}"


settings = Settings()


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "comics").mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "avatars").mkdir(parents=True, exist_ok=True)
