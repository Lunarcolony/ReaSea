import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "papers.db"
conn = sqlite3.connect(db)
count = conn.execute("SELECT COUNT(*) FROM saved_papers").fetchone()[0]
rows = conn.execute("SELECT paper_id FROM saved_papers LIMIT 10").fetchall()
print(f"saved_papers count: {count}")
print(f"sample ids: {[r[0] for r in rows]}")
