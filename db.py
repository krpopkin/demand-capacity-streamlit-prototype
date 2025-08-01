import os
import sqlalchemy
from dotenv import load_dotenv

load_dotenv()

_engine = None  # Singleton engine reference

def is_cloud_run():
    return os.getenv("K_SERVICE") is not None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")

    if is_cloud_run():
        DB_HOST = "/cloudsql/amw-dna-coe-working-ds-dev:us-central1:demand-capacity"
        conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={DB_HOST}"
    else:
        DB_HOST = "130.211.120.38"
        DB_PORT = "5432"
        conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    _engine = sqlalchemy.create_engine(
        conn_str,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=2,
        isolation_level="AUTOCOMMIT",
    )
    return _engine

def get_connection():
    return get_engine().connect()
