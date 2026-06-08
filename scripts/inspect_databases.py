"""Inspect SQLite databases under the project."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(path: Path):
    if not path.exists():
        return
    conn = sqlite3.connect(path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"\n{path} ({path.stat().st_size:,} bytes)")
        for (name,) in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
                print(f"  {name}: {count}")
            except Exception as e:
                print(f"  {name}: error {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    for db in sorted(ROOT.rglob("*.db")):
        if any(p in db.parts for p in (".venv", "venv", "node_modules")):
            continue
        inspect(db)
