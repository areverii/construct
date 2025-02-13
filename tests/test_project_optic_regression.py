import os
import pytest
from sqlalchemy import select

from construct.database import init_db, pddl_mappings_table
from construct.scheduler import run_optic

# We assume the default database (or file-based database) is used that was updated by the workflow regression test.
@pytest.fixture(scope="session")
def engine():
    return init_db()

@pytest.fixture(scope="session")
def schedule_id():
    # This is the schedule identifier used in your workflow regression test.
    # Adjust if you use a different schedule for the target ingestion.
    return "TARGET001"

@pytest.mark.run(order=2)
# @pytest.mark.dependency(depends=["workflow"])
def test_optic_scheduler_regression(engine, schedule_id):
    """
    Regression test for the optic scheduler.
    
    Pre-conditions:
      - The workflow regression test has run and generated the PDDL mapping.
      
    This test:
      1. Retrieves the PDDL mapping from the database for the given schedule_id.
      2. Verifies that both the domain and problem PDDL files exist.
      3. Calls the optic scheduler to generate an optimized schedule.
      4. Asserts that the result from the optic scheduler indicates success and that
         the optimized project file exists.
    """
    # ---- Retrieve the PDDL mapping generated by the workflow regression test ----
    with engine.connect() as conn:
        mapping = conn.execute(
            select(pddl_mappings_table).where(
                pddl_mappings_table.c.schedule_id == schedule_id
            )
        ).mappings().fetchone()
    
    assert mapping, f"No PDDL mapping found for schedule_id '{schedule_id}'. Ensure the workflow regression test has run."
    domain_file = mapping["domain_file"]
    problem_file = mapping["problem_file"]
    
    for file in (domain_file, problem_file):
        assert os.path.isfile(file), f"PDDL file not found: {file}"
    
    # ---- Call the optic scheduler ----
    # We assume the optimizer uses the schedule_id, the engine, and the mapping (which contains the file paths)
    result = run_optic(schedule_id, engine, mapping)
    
    # The optimizer should return a dictionary that includes a 'status' key and an optimized project file.
    assert isinstance(result, dict), "Optic scheduler result is not a dictionary"
    assert result.get("status") == "success", f"Optic scheduler did not complete successfully: {result}"
    
    optimized_project_file = result.get("optimized_project_file")
    assert optimized_project_file, "Optic scheduler result lacks 'optimized_project_file' field"
    assert os.path.isfile(optimized_project_file), f"Optimized project file not found: {optimized_project_file}"