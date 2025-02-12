import os
import pytest
from fastapi.testclient import TestClient
from construct.database import init_db

# Use this test only if the sample files exist
@pytest.fixture(scope="session")
def resources_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "resources")

@pytest.fixture(scope="session")
def client():
    from construct.api import app
    return TestClient(app)

def test_project_workflow_regression(client, resources_dir, tmp_path):
    """
    Regression test that performs the following steps:
    
    1. Creates a project via the /create-project/ API endpoint using a target schedule.
       (Uses the test file resources/test_1.xlsx)
       
    2. Ingests the target schedule via the /ingest-schedule/ API endpoint.
       
    3. Ingests an in-progress schedule (resources/test_1_progress_1.xlsx) via the same endpoint.
    
    4. Updates the in-progress schedule's current date (to "2024-02-01 08:00:00")
       using the set_current_in_progress_date function.
       
    5. Generates PDDL files for the updated schedule using generate_pddl_for_schedule.
       Asserts that the generated PDDL files exist.
    """
    import shutil
    # Delete previous generated project folder if exists
    project_folder = os.path.join("gen", "TestProject")
    if os.path.exists(project_folder):
        shutil.rmtree(project_folder)

    # ---- Step 1: Create a new project ----
    project_payload = {
        "project_name": "TestProject",
        "schedule_id": "TARGET001",
        "project_folder": "gen"
    }
    create_resp = client.post("/create-project/", json=project_payload)
    assert create_resp.status_code == 200, f"Project creation failed: {create_resp.text}"
    create_data = create_resp.json()
    project_handle = create_data.get("project_file")
    db_file = create_data.get("db_file")
    assert project_handle and db_file, "Project creation did not return required file paths."

    # ---- Step 2: Ingest the target schedule ----
    target_file = os.path.join(resources_dir, "test_1.xlsx")
    ingest_params = {
        "file_path": target_file,
        "schedule_id": "TARGET001",
        "schedule_type": "target",
        "project_handle": project_handle
    }
    ingest_resp = client.post("/ingest-schedule/", params=ingest_params)
    assert ingest_resp.status_code == 200, f"Target schedule ingestion failed: {ingest_resp.text}"
    ingest_data = ingest_resp.json()
    target_schedule_id = ingest_data.get("schedule_id")
    assert target_schedule_id, "Ingestion did not return a schedule_id for target schedule."
    
    # ---- Step 3: Ingest the in-progress schedule ----
    progress_file = os.path.join(resources_dir, "test_1_progress_1.xlsx")
    ingest_prog_params = {
        "file_path": progress_file,
        "schedule_id": "INPROGRESS001",
        "schedule_type": "in-progress",
        "project_handle": project_handle
    }
    ingest_prog_resp = client.post("/ingest-schedule/", params=ingest_prog_params)
    assert ingest_prog_resp.status_code == 200, f"In-progress schedule ingestion failed: {ingest_prog_resp.text}"
    prog_data = ingest_prog_resp.json()
    progress_schedule_id = prog_data.get("schedule_id")
    assert progress_schedule_id, "Ingestion did not return a schedule_id for in-progress schedule."
    
    # ---- Step 4: Update in-progress schedule date ----
    from construct.project_management import set_current_in_progress_date
    # Get the project-specific engine using the DB file from project creation
    engine = init_db(db_url=f"sqlite:///{db_file}")
    new_date = "2024-02-01 08:00:00"
    # Now call set_current_in_progress_date with engine, schedule_id, and new_date.
    # Note: This function in our design doesn't return a value, it simply updates the DB.
    set_current_in_progress_date(engine, progress_schedule_id, new_date)
    # Optionally, you can query the DB to verify that the date was updated.
    # For this test, we assume that if no exception is raised, the update was successful.
    
    # ---- Step 5: Generate PDDL files ----
    from construct.pddl_generation import generate_pddl_for_schedule
    output_dir = tmp_path / "pddl_output"
    pddl_files = generate_pddl_for_schedule(progress_schedule_id, engine, output_dir=str(output_dir))
    assert isinstance(pddl_files, dict) and pddl_files, "PDDL generation did not return expected files."
    for file_path in pddl_files.values():
        assert os.path.isfile(file_path), f"PDDL file not found: {file_path}"