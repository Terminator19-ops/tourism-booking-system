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

    cursor = connection.cursor()
    cursor.execute("SELECT USER FROM DUAL")

    result = cursor.fetchone()

    print("Connected as:", result[0])

    cursor.close()
    connection.close()

except Exception as e:
    print("Oracle connection failed!")
    print("Error:", e)