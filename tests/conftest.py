import os
import pytest
from fastapi.testclient import TestClient
from construct.api import app
from construct.database import init_db

@pytest.fixture(scope="session")
def test_client():
    """
    Provides a FastAPI TestClient for API regression tests.
    """
    client = TestClient(app)
    yield client

@pytest.fixture(scope="session")
def resources_dir():
    """
    Returns the absolute path to the resources folder.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "resources")

@pytest.fixture(scope="session")
def sample_schedule_xlsx(resources_dir):
    """
    Provides the full path to the sample XLSX schedule file for regression tests.
    Expects a file named 'test_1.xlsx' inside the resources folder.
    Skips tests if the file is missing.
    """
    sample_file = os.path.join(resources_dir, "test_1.xlsx")
    if not os.path.exists(sample_file):
        pytest.skip("Sample XLSX schedule file not found in resources.")
    return sample_file