# tests/test_project_workflow.py
import os
import uuid
import pytest
from sqlalchemy import text
from construct.project import create_project
from construct.database import init_db
from construct.ingestion import ingest_schedule_data
from construct.project_management import set_current_in_progress_date

# Option to clean up the project folder after tests.
CLEANUP_AFTER_TEST = False

@pytest.fixture
def unique_project_folder():
    unique_id = uuid.uuid4().hex
    project_folder = os.path.join("gen", f"test_project_{unique_id}")
    os.makedirs(project_folder, exist_ok=True)
    yield project_folder
    if CLEANUP_AFTER_TEST:
        import shutil
        shutil.rmtree(project_folder)

def test_project_workflow(unique_project_folder):
    project_name = "Test Project Workflow"
    schedule_id = "240001"  # Use one schedule ID for the entire workflow.
    
    # Create the project.
    # This function creates a .cproj file and a DB file in the project folder.
    project_file, db_file = create_project(project_name, schedule_id, unique_project_folder)
    
    # Use the DB file in the project folder for our database URI.
    db_url = f"sqlite:///{os.path.abspath(db_file)}"
    engine = init_db(db_url=db_url)
    
    # Ingest the target schedule.
    # (This ingestion triggers PDDL generation for the target schedule.)
    ingest_schedule_data(
        file_path="resources/test_1.xlsx",
        schedule_id=schedule_id,
        schedule_type="target",
        engine=engine,
        auto_generate_pddl=True
    )
    
    # Ingest the in-progress schedule.
    ingest_schedule_data(
        file_path="resources/test_1_progress_1.xlsx",
        schedule_id=schedule_id,
        schedule_type="in-progress",
        engine=engine
    )
    
    # Set the current in-progress date.
    set_current_in_progress_date(
        engine=engine,
        schedule_id=schedule_id,
        user_date_str="2024-02-01 08:00:00"
    )
    
    # Verify that a PDDL mapping was inserted and that the PDDL files exist in the project folder.
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM pddl_mappings WHERE schedule_id = :schedule_id"),
            {"schedule_id": schedule_id}
        ).mappings().fetchone()
    assert row is not None, "PDDL mapping not found for schedule_id=240001"
    domain_file = row["domain_file"]
    problem_file = row["problem_file"]
    assert os.path.exists(domain_file), f"Domain file not found: {domain_file}"
    assert os.path.exists(problem_file), f"Problem file not found: {problem_file}"
    
    project_folder_abs = os.path.abspath(unique_project_folder)
    assert project_folder_abs in os.path.abspath(domain_file), "Domain file not in project folder"
    assert project_folder_abs in os.path.abspath(problem_file), "Problem file not in project folder"
    
    # --- Simulate a task update ---
    # Re-ingest the in-progress schedule to simulate updated task progress.
    ingest_schedule_data(
        file_path="resources/test_1_progress_1.xlsx",
        schedule_id=schedule_id,
        schedule_type="in-progress",
        engine=engine
    )
    
    # Re-check the PDDL mapping to ensure it is still the same (i.e. we update the same project).
    with engine.connect() as conn:
        row_after = conn.execute(
            text("SELECT * FROM pddl_mappings WHERE schedule_id = :schedule_id"),
            {"schedule_id": schedule_id}
        ).mappings().fetchone()
    assert row_after is not None, "PDDL mapping lost after update"
    assert row_after["domain_file"] == domain_file, "Domain file changed after update"
    assert row_after["problem_file"] == problem_file, "Problem file changed after update"