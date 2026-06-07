"""FastAPI backend for Research Feed."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import feed, papers, search, users
from database import init_db, SessionLocal
from api.single_user import ensure_default_user

app = FastAPI(title="Research Feed API", version="1.0.0")

_cors_origins = os.getenv("CORS_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins.split(",") if _cors_origins else [],
    allow_origin_regex=None if _cors_origins else r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feed.router, prefix="/feed", tags=["feed"])
app.include_router(papers.router, prefix="/papers", tags=["papers"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        ensure_default_user(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
