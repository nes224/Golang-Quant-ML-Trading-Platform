from app.core.database import db

def clear_bad_cache():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            print("Clearing cache for DX-Y.NYB and ^TNX...")
            cur.execute("DELETE FROM market_data WHERE symbol IN ('DX-Y.NYB', '^TNX')")
            conn.commit()
            print(f"Deleted {cur.rowcount} rows.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)

if __name__ == "__main__":
    clear_bad_cache()
