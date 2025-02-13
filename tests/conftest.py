import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from construct.api import app  # your FastAPI app
from construct.database import metadata

@pytest.fixture(scope="session")
def resources_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "resources")

@pytest.fixture(scope="session")
def db_url(tmp_path_factory):
    # Create a temporary SQLite database file.
    db_dir = tmp_path_factory.mktemp("data")
    db_path = db_dir / "test.db"
    return f"sqlite:///{db_path}"

@pytest.fixture(scope="session")
def engine(db_url):
    engine = create_engine(db_url)
    metadata.create_all(bind=engine)
    yield engine
    metadata.drop_all(bind=engine)

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c