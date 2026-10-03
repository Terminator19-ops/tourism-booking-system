import os
import oracledb
from dotenv import load_dotenv

# Where this file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env from the same folder as this file
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Resolve wallet path relative to this file
WALLET_DIR = os.path.abspath(os.path.join(BASE_DIR, os.getenv("WALLET_DIR")))

def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN"),
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=os.getenv("WALLET_PASSWORD")
    )

if __name__ == "__main__":
    print("BASE_DIR:", BASE_DIR)
    print("WALLET_DIR:", WALLET_DIR)
    print("DB_USER:", os.getenv("DB_USER"))
    print("DB_DSN:", os.getenv("DB_DSN"))
    conn = get_connection()
    print("Connected to Oracle:", conn.version)
    conn.close()