import os
from dotenv import load_dotenv

ENV_FILE = "/home/terminator18ops/Documents/Aditya/SEM-5/DBMS/Project/.env"

loaded = load_dotenv(ENV_FILE)

print("dotenv loaded:", loaded)

wallet_dir = os.getenv("ORACLE_WALLET_DIR")
user = os.getenv("ORACLE_USER")
password = os.getenv("ORACLE_PASSWORD")

print("wallet_dir =", wallet_dir)
print("user =", user)
print("password exists =", password is not None)
print("wallet exists =", os.path.exists(wallet_dir) if wallet_dir else False)