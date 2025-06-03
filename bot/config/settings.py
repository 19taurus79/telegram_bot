import os
from dotenv import load_dotenv

load_dotenv() # Загружаем переменные окружения из .env

class Settings:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    # ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", 12345))

    # Database
    DB_HOST: str = os.getenv("POSTGRES_HOST")
    DB_PORT: int = int(os.getenv("POSTGRES_PORT"))
    DB_USER: str = os.getenv("POSTGRES_USER")
    DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    DB_NAME: str = os.getenv("POSTGRES_DB")

    # Paths
    UPLOAD_DIRECTORY: str = "uploaded_files"
    MEDIA_URL: str = "/media/"

settings = Settings()

# Убедимся, что директория для загрузок существует
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)