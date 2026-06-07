import sys
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test_papers.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from database import init_db, engine, Base
from api.main import app


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as c:
        yield c
