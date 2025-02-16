import os
import json
import pytest
from datetime import datetime
from sqlalchemy import select, create_engine
from construct.database import projects_table, tasks_table, pddl_mappings_table
from construct.api import app
from construct.project_management import set_current_in_progress_date  # a helper function

# Global dictionary to share state between tests.
workflow_state = {}

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ------------------------------------------------------------------
# TEST 1: Create the Project (Target)
# ------------------------------------------------------------------
@pytest.mark.run(order=1)
@pytest.mark.dependency(name="create_project")
def test_create_project(client):
    project_payload = {
        "project_name": "TestProject",
        "schedule_id": "TARGET001",
        # Provide an absolute folder path (here using the "gen" folder)
        "project_folder": os.path.abspath("gen")
    }
    response = client.post("/create-project/", json=project_payload)
    assert response.status_code == 200, f"Project creation failed: {response.text}"
    data = response.json()
    # Expect the response to include file paths for project handle and the database file.
    assert "project_file" in data, "Missing 'project_file' in create-project response"
    assert "db_file" in data, "Missing 'db_file' in create-project response"
    workflow_state["project_handle"] = data["project_file"]
    workflow_state["db_file"] = data["db_file"]

# ------------------------------------------------------------------
# TEST 2: Ingest the Target Schedule via API
# ------------------------------------------------------------------
@pytest.mark.run(order=2)
@pytest.mark.dependency(name="ingest_target", depends=["create_project"])
def test_ingest_target_schedule(client, resources_dir):
    project_handle = workflow_state.get("project_handle")
    assert project_handle, "Project handle not found from previous test"

    target_file = os.path.join(resources_dir, "test_1.xlsx")
    ingest_params = {
        "file_path": target_file,
        "schedule_id": "TARGET001",
        "schedule_type": "target",
        "project_handle": project_handle
    }
    response = client.post("/ingest-schedule/", params=ingest_params)
    assert response.status_code == 200, f"Target schedule ingestion failed: {response.text}"
    data = response.json()
    assert data.get("schedule_id") == "TARGET001", "Target schedule ingestion did not return expected schedule_id"

# ------------------------------------------------------------------
# TEST 3: Validate the Target Project's Data and PDDL Mapping in the DB
# ------------------------------------------------------------------
@pytest.mark.run(order=3)
@pytest.mark.dependency(name="validate_target", depends=["ingest_target"])
def test_validate_target_project_data():
    db_file = workflow_state.get("db_file")
    assert db_file, "DB file not found in workflow_state"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.connect() as conn:
        project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "TARGET001")
        ).mappings().fetchone()
    assert project, "Target project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        assert project[col], f"Column '{col}' is empty in target project record"

    # Validate the PDDL mapping for the target schedule.
    with engine.connect() as conn:
        mapping = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "TARGET001")
        ).mappings().fetchone()
    assert mapping, "No PDDL mapping found for target schedule"
    assert mapping["domain_file"], "Domain file mapping is empty for target schedule"
    # For a target schedule, the problem_file should be None.
    assert mapping["problem_file"] is None, "Problem file should be empty for target schedule"

# ------------------------------------------------------------------
# TEST 4: Ingest the In-Progress Schedule via API
# ------------------------------------------------------------------
@pytest.mark.run(order=4)
@pytest.mark.dependency(name="ingest_progress", depends=["create_project"])
def test_ingest_inprogress_schedule(client, resources_dir):
    project_handle = workflow_state.get("project_handle")
    assert project_handle, "Project handle not found from create_project"

    progress_file = os.path.join(resources_dir, "test_1_progress_1.xlsx")
    ingest_params = {
        "file_path": progress_file,
        "schedule_id": "INPROGRESS001",
        "schedule_type": "in-progress",
        "project_handle": project_handle
    }
    response = client.post("/ingest-schedule/", params=ingest_params)
    assert response.status_code == 200, f"In-progress schedule ingestion failed: {response.text}"
    data = response.json()
    assert data.get("schedule_id") == "INPROGRESS001", "Ingestion did not return expected in-progress schedule_id"

# ------------------------------------------------------------------
# TEST 5: Validate the In-Progress Project's Data in the DB
# ------------------------------------------------------------------
@pytest.mark.run(order=5)
@pytest.mark.dependency(name="validate_inprogress", depends=["ingest_progress"])
def test_validate_inprogress_project_data():
    db_file = workflow_state.get("db_file")
    assert db_file, "DB file not found in workflow_state"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.connect() as conn:
        project = conn.execute(
            select(projects_table).where(projects_table.c.schedule_id == "INPROGRESS001")
        ).mappings().fetchone()
    assert project, "In-progress project row not found in the database"
    for col in ["schedule_id", "project_name", "created_at", "schedule_type"]:
        assert project[col], f"Column '{col}' is empty in in-progress project record"

# ------------------------------------------------------------------
# TEST 6: Update the In-Progress Schedule Current Date 
# ------------------------------------------------------------------
@pytest.mark.run(order=6)
@pytest.mark.dependency(name="update_inprogress_date", depends=["validate_inprogress"])
def test_update_inprogress_schedule_date():
    db_file = workflow_state.get("db_file")
    assert db_file, "DB file not found in workflow_state"
    engine = create_engine(f"sqlite:///{db_file}")

    new_date = "2024-02-01 08:00:00"
    set_current_in_progress_date(engine, "INPROGRESS001", new_date)
    with engine.connect() as conn:
        updated_date = conn.execute(
            select(projects_table.c.current_in_progress_date)
            .where(projects_table.c.schedule_id == "INPROGRESS001")
        ).scalar()
    assert updated_date == new_date, "In-progress schedule date was not updated correctly in the database"

# ------------------------------------------------------------------
# TEST 7: Validate the In-Progress Schedule's PDDL Mapping in the DB
# ------------------------------------------------------------------
@pytest.mark.run(order=7)
@pytest.mark.dependency(name="validate_progress_pddl", depends=["update_inprogress_date"])
def test_validate_inprogress_pddl_mapping():
    db_file = workflow_state.get("db_file")
    assert db_file, "DB file not found in workflow_state"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.connect() as conn:
        mapping = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "INPROGRESS001")
        ).mappings().fetchone()
    assert mapping, "No PDDL mapping found for in-progress schedule"
    assert mapping["domain_file"], "Domain file mapping is empty for in-progress schedule"
    assert mapping["problem_file"], "Problem file mapping is empty for in-progress schedule"

# ------------------------------------------------------------------
# TEST 8: Validate Ingestion of Baseline Dates for Chunking
# ------------------------------------------------------------------
pytest.mark.run(order=8)
@pytest.mark.dependency(name="validate_ingestion_dates", depends=["validate_progress_pddl"])
def test_ingestion_dates_regression():
    """
    This test verifies that tasks from the TARGET schedule have either both
    a 'bl_start' and 'bl_finish' date (which can be parsed using DATE_FORMAT)
    or neither is provided (which is acceptable). It fails if exactly one
    value is missing.
    """
    db_file = workflow_state.get("db_file")
    assert db_file, "DB file not found in workflow_state"
    engine = create_engine(f"sqlite:///{db_file}")
    
    with engine.connect() as conn:
        rows = conn.execute(
            select(tasks_table).where(tasks_table.c.schedule_id == "TARGET001")
        ).mappings().all()
    assert rows, "No tasks found for schedule TARGET001"
    
    for row in rows:
        task_id = row["task_id"]
        bl_start = row.get("bl_start")
        bl_finish = row.get("bl_finish")
        
        # Fail if exactly one date is missing.
        if (bl_start and not bl_finish) or (bl_finish and not bl_start):
            pytest.fail(f"Task {task_id} has only one baseline date: bl_start: {bl_start}, bl_finish: {bl_finish}")
        # If both dates are missing, that's acceptable.
        elif not bl_start and not bl_finish:
            continue
        # Both dates are present; ensure they can be parsed.
        try:
            datetime.strptime(bl_start, DATE_FORMAT)
        except Exception as e:
            pytest.fail(f"Task {task_id} has an invalid 'bl_start' value '{bl_start}': {e}")
        try:
            datetime.strptime(bl_finish, DATE_FORMAT)
        except Exception as e:
            pytest.fail(f"Task {task_id} has an invalid 'bl_finish' value '{bl_finish}': {e}")