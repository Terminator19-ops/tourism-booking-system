
import os
from pathlib import Path

from dotenv import load_dotenv
import oracledb


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

WALLET_DIR = Path(__file__).resolve().parents[2] / "wallet"

_pool = None


def _get_pool():
    global _pool

    if _pool is None:
        _pool = oracledb.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dsn=os.getenv("DB_DSN"),
            config_dir=str(WALLET_DIR),
            wallet_location=str(WALLET_DIR),
            wallet_password=os.getenv("WALLET_PASSWORD"),
            min=2,
            max=10,
            increment=1,
        )

    return _pool


def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN"),
        config_dir=str(WALLET_DIR),
        wallet_location=str(WALLET_DIR),
        wallet_password=os.getenv("WALLET_PASSWORD"),
    )
