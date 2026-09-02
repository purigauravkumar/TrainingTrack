from app import DB_PATH

if DB_PATH.exists():
    DB_PATH.unlink()
    print(f"Deleted {DB_PATH}")
else:
    print("Database does not exist; nothing to reset.")
