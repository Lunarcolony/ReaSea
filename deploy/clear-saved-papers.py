import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "papers.db"
conn = sqlite3.connect(db)
cur = conn.execute("DELETE FROM saved_papers")
conn.commit()
print(f"cleared {cur.rowcount} rows from saved_papers")
