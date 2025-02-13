import os
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from construct.database import init_db, projects_table, pddl_mappings_table
from construct.project_management import set_current_in_progress_date
from construct.pddl_generation import generate_pddl_for_schedule

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
    Full regression test for the project workflow that:
      1. Creates a project via /create-project/
      2. Ingests the target schedule
      3. Ingestes an in-progress schedule
      4. Updates the in-progress schedule's current date
      5. Generates PDDL files

    Additionally, the test validates that the ingested data stored in the
    database (projects and PDDL mappings) contains non-empty values for
    all required fields.
    """
    # Delete previous generated project folder if exists.
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

    # ---- Validate database content for target schedule ----
    engine = init_db(db_url=f"sqlite:///{db_file}")
    with engine.connect() as conn:
        target_project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "TARGET001")
        ).mappings().fetchone()
    assert target_project, "Target project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        value = target_project[col]
        assert value, f"Column '{col}' is empty in target project record"

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

    # ---- Validate database content for in-progress schedule ----
    with engine.connect() as conn:
        inprogress_project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "INPROGRESS001")
        ).mappings().fetchone()
    assert inprogress_project, "In-progress project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        value = inprogress_project[col]
        assert value, f"Column '{col}' is empty in in-progress project record"

    # ---- Step 4: Update in-progress schedule date ----
    new_date = "2024-02-01 08:00:00"
    set_current_in_progress_date(engine, progress_schedule_id, new_date)
    with engine.connect() as conn:
        updated_date = conn.execute(
            select(projects_table.c.current_in_progress_date)
            .where(projects_table.c.schedule_id == "INPROGRESS001")
        ).scalar()
    assert updated_date == new_date, "In-progress schedule date not updated in database"

    # ---- Step 5: Generate PDDL files ----
    output_dir = tmp_path / "pddl_output"
    pddl_files = generate_pddl_for_schedule(progress_schedule_id, engine, output_dir=str(output_dir))
    assert isinstance(pddl_files, dict) and pddl_files, "PDDL generation did not return expected files."
    for file_path in pddl_files.values():
        assert os.path.isfile(file_path), f"PDDL file not found: {file_path}"

    # ---- Validate PDDL mapping in the database ----
    with engine.connect() as conn:
        mapping = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == progress_schedule_id)
        ).mappings().fetchone()
    assert mapping, "No PDDL mapping found for the progress schedule"
    for col in ["domain_file", "problem_file"]:
        value = mapping[col]
        assert value, f"PDDL mapping column '{col}' is empty"