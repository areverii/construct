# tests/test_project_creation.py
import os
import uuid
import pytest
from construct.project import create_project

# Set this to True if you want the test to remove the files after it runs.
CLEANUP_AFTER_TEST = False

@pytest.fixture
def unique_project_folder():
    # Create a unique folder in "gen" for the test project.
    unique_id = uuid.uuid4().hex
    project_folder = os.path.join("gen", f"test_project_{unique_id}")
    os.makedirs(project_folder, exist_ok=True)
    yield project_folder
    if CLEANUP_AFTER_TEST:
        import shutil
        shutil.rmtree(project_folder)

def test_create_project_file_and_db(unique_project_folder):
    project_name = "Test Project Creation"
    schedule_id = "TEST123"
    project_file, db_file = create_project(project_name, schedule_id, unique_project_folder)
    # Verify the project file exists
    assert os.path.exists(project_file), f"Project file {project_file} does not exist"
    # Verify the database file exists
    assert os.path.exists(db_file), f"Database file {db_file} does not exist"