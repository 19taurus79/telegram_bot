from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
from dotenv import load_dotenv
import os

load_dotenv()
DB = PostgresEngine(
    config={
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT")),
    }
)
APP_REGISTRY = AppRegistry(apps=["bot_tables.piccolo_app"])
