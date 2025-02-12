# tests/test_integration_real_db.py
import os
import pytest
from sqlalchemy import select
from construct.database import init_db, pddl_mappings_table
from construct.ingestion import ingest_schedule_data
from construct.project_management import set_current_in_progress_date
from construct.agent import ConstructionAgent

TEST_DB_PATH = "gen/construct_test_integration.db"

@pytest.mark.order(1)
def test_full_integration_db():
    # Remove any leftover test db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Initialize a fresh engine for this test db
    engine = init_db(db_url=f"sqlite:///{TEST_DB_PATH}")

    # Ingest target schedule and trigger PDDL generation
    ingest_schedule_data(
        file_path="resources/test_1.xlsx",
        schedule_id="240001",
        schedule_type="target",
        engine=engine,
        auto_generate_pddl=True  # triggers PDDL creation
    )

    # Ingest in-progress schedule
    ingest_schedule_data(
        file_path="resources/test_1_progress_1.xlsx",
        schedule_id="240001",
        schedule_type="in-progress",
        engine=engine
    )

    # Set current date so the agent can compare actual vs expected progress
    set_current_in_progress_date(
        engine=engine,
        schedule_id="240001",
        user_date_str="2024-02-01 08:00:00"  # from the README example
    )

    # Confirm that PDDL mapping and files were generated
    with engine.connect() as conn:
        row = conn.execute(
            select(pddl_mappings_table).where(
                pddl_mappings_table.c.schedule_id == "240001"
            )
        ).fetchone()
        assert row, "PDDL mapping not found for schedule_id=240001"
        assert os.path.exists(row.domain_file), f"Domain file not found: {row.domain_file}"
        assert os.path.exists(row.problem_file), f"Problem file not found: {row.problem_file}"

    # Load the generated domain file and check for expected new constructs
    with open(row.domain_file, "r") as f:
        domain_contents = f.read()
    # Assert that the domain declares both 'task' and 'chunk' types
    assert "(:types task chunk)" in domain_contents, "Missing types declaration for task and chunk"
    # Assert that the new predicates appear
    for predicate in ["(done ?t - task)", "(in-chunk ?t - task ?c - chunk)", "(chunk-order ?c1 - chunk ?c2 - chunk)"]:
        assert predicate in domain_contents, f"Missing predicate declaration: {predicate}"
    # Optionally, verify that at least one action includes an in-chunk condition:
    assert "(in-chunk" in domain_contents, "No in-chunk conditions found in actions"

    # Optionally, load the problem file and verify that chunk objects are declared and tasks are assigned to chunks
    with open(row.problem_file, "r") as f:
        problem_contents = f.read()
    for chunk_label in [ "chunk_0", "chunk_1", "chunk_2" ]:
        assert chunk_label in problem_contents, f"Chunk {chunk_label} not found in problem definition"
    # And that there is a chunk-order predicate somewhere:
    assert "chunk-order" in problem_contents, "Missing chunk-order information in problem file"

    # Run analysis to ensure behind/ahead tasks are identified.
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress("240001")
    print("Analysis result:", result)
    assert "schedule_id" in result
    assert "insights" in result
    # Optional: check if there’s at least one behind-schedule or ahead-of-schedule message.
    assert result["insights"], "No schedule insights found"