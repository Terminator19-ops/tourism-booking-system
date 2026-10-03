import os
from pathlib import Path

from dotenv import load_dotenv
import oracledb

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

WALLET_DIR = (BASE_DIR / os.getenv("WALLET_DIR", "wallet")).resolve()


def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN"),
        config_dir=str(WALLET_DIR),
        wallet_location=str(WALLET_DIR),
        wallet_password=os.getenv("WALLET_PASSWORD"),
    )
