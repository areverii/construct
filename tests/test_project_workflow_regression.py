import os
import pytest
from datetime import datetime, timedelta
from construct.ingestion import ingest_schedule_data
from construct.project_management import set_current_in_progress_date
from construct.pddl_generation import generate_pddl_for_schedule
from construct.database import init_db

def test_project_workflow_regression(sample_schedule_xlsx, tmp_path):
    """
    Regression test for the overall project workflow:
      1. Initializes a temporary database.
      2. Ingests schedule data from an XLSX file.
      3. Simulates a task update on the in-progress schedule.
      4. Generates PDDL files based on the updated schedule.
    
    (The scheduling step is omitted until the supporting code is ready.)
    """
    # Step 1: Initialize a temporary database.
    test_db_path = tmp_path / "test_project_workflow_regression.db"
    engine = init_db(db_url=f"sqlite:///{test_db_path}")
    
    # Step 2: Ingest schedule data.
    schedule_data = ingest_schedule_data(str(sample_schedule_xlsx), schedule_type="target", engine=engine)
    assert schedule_data is not None, "Failed to ingest schedule data."
    
    # Capture the original date (if present).
    original_date = getattr(schedule_data, 'current_date', None)
    
    # Step 3: Simulate a task update.
    new_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
    updated_schedule = set_current_in_progress_date(schedule_data, new_date)
    assert updated_schedule is not None, "Failed to update schedule date."
    assert getattr(updated_schedule, 'current_date', None) == new_date, "Schedule date was not updated correctly."
    
    # Step 4: Generate PDDL files.
    # Assume generate_pddl_for_schedule returns a dictionary with file paths.
    output_dir = tmp_path / "pddl_output"
    pddl_files = generate_pddl_for_schedule(updated_schedule, output_dir=str(output_dir))
    
    assert isinstance(pddl_files, dict) and pddl_files, "PDDL generation did not return expected files."
    for file_path in pddl_files.values():
        assert os.path.isfile(file_path), f"PDDL file not found: {file_path}"