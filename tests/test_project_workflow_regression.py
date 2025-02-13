import os
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from construct.database import init_db, projects_table, pddl_mappings_table

@pytest.fixture(scope="session")
def resources_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "resources")

@pytest.fixture(scope="session")
def client():
    from construct.api import app
    return TestClient(app)

@pytest.mark.run(order=1)
@pytest.mark.dependency(name="workflow")
def test_project_workflow_regression(client, resources_dir, tmp_path):
    """
    Full regression test for the project workflow via API endpoints.
    """
    # Delete previous generated project folder if exists.
    project_folder = os.path.join("gen", "TestProject")
    if os.path.exists(project_folder):
        shutil.rmtree(project_folder)
        
    # ---- Step 1: Create a new project using the API endpoint ----
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
    
    # ---- Step 2: Ingest the target schedule via API ----
    target_file = os.path.join(resources_dir, "test_1.xlsx")
    ingest_params_target = {
        "file_path": target_file,
        "schedule_id": "TARGET001",
        "schedule_type": "target",
        "project_handle": project_handle
    }
    ingest_resp_target = client.post("/ingest-schedule/", params=ingest_params_target)
    assert ingest_resp_target.status_code == 200, f"Target schedule ingestion failed: {ingest_resp_target.text}"
    ingest_data_target = ingest_resp_target.json()
    target_schedule_id = ingest_data_target.get("schedule_id")
    assert target_schedule_id, "Ingestion did not return a schedule_id for target schedule."
    
    # ---- Validate database content for target project ----
    engine = init_db(db_url=f"sqlite:///{db_file}")
    with engine.connect() as conn:
        target_project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "TARGET001")
        ).mappings().fetchone()
    assert target_project, "Target project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        value = target_project[col]
        assert value, f"Column '{col}' is empty in target project record"
        
    # ---- Validate PDDL mapping for target schedule ----
    with engine.connect() as conn:
        target_mapping = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "TARGET001")
        ).mappings().fetchone()
    assert target_mapping, "No PDDL mapping found for target schedule"
    assert target_mapping["domain_file"], "Domain file mapping is empty for target schedule"
    # For a target schedule, problem_file should be None.
    assert target_mapping["problem_file"] is None, "Problem file should be empty for target schedule"
        
    # ---- Step 3: Ingest the in-progress schedule via API ----
    progress_file = os.path.join(resources_dir, "test_1_progress_1.xlsx")
    ingest_params_progress = {
        "file_path": progress_file,
        "schedule_id": "INPROGRESS001",
        "schedule_type": "in-progress",
        "project_handle": project_handle
    }
    ingest_prog_resp = client.post("/ingest-schedule/", params=ingest_params_progress)
    assert ingest_prog_resp.status_code == 200, f"In-progress schedule ingestion failed: {ingest_prog_resp.text}"
    prog_data = ingest_prog_resp.json()
    progress_schedule_id = prog_data.get("schedule_id")
    assert progress_schedule_id, "Ingestion did not return a schedule_id for in-progress schedule."
    
    # ---- Validate database content for in-progress project ----
    with engine.connect() as conn:
        inprogress_project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "INPROGRESS001")
        ).mappings().fetchone()
    assert inprogress_project, "In-progress project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        value = inprogress_project[col]
        assert value, f"Column '{col}' is empty in in-progress project record"
        
    # ---- Step 4: Update in-progress schedule date ----
    from construct.project_management import set_current_in_progress_date
    new_date = "2024-02-01 08:00:00"
    set_current_in_progress_date(engine, progress_schedule_id, new_date)
    with engine.connect() as conn:
        updated_date = conn.execute(
            select(projects_table.c.current_in_progress_date)
            .where(projects_table.c.schedule_id == "INPROGRESS001")
        ).scalar()
    assert updated_date == new_date, "In-progress schedule date not updated in database"
    
    # ---- Step 5: Validate PDDL mapping for in-progress schedule ----
    # The ingestion endpoint now uses the event handler (registered during project creation)
    # to trigger idempotent generation of PDDL files.
    with engine.connect() as conn:
        progress_mapping = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "INPROGRESS001")
        ).mappings().fetchone()
    assert progress_mapping, "No PDDL mapping found for the in-progress schedule"
    assert progress_mapping["domain_file"], "Domain file mapping is empty for in-progress schedule"
    assert progress_mapping["problem_file"], "Problem file mapping is empty for in-progress schedule"