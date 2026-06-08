"""Canonical project paths — single source of truth for the SQLite database location."""

from pathlib import Path

# Project root (parent of this file's directory when placed at project root)
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LEGACY_DB_PATH = PROJECT_ROOT / "papers.db"
CANONICAL_DB_PATH = DATA_DIR / "papers.db"
