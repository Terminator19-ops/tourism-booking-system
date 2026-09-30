import oracledb

WALLET_DIR = "/home/terminator18ops/Documents/Aditya/SEM-5/DBMS/Project/oracle_wallet"

try:
    print("Connecting to Oracle...")

    connection = oracledb.connect(
        user="PROJECT",
        password="Zebra#7391Moon",
        dsn="dbmsproject_low",
        config_dir=WALLET_DIR,
    )

    print("Oracle connection successful!")

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()

    print(f"Test query result: {result[0]}")

    connection.close()

except Exception as e:
    print("Oracle connection failed!")
    print(f"Error: {e}")

    