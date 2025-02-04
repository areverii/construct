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
    # remove any leftover test db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # init a fresh engine for this test db
    engine = init_db(db_url=f"sqlite:///{TEST_DB_PATH}")

    # ingest target schedule with new (optimized) PDDL generation enabled.
    ingest_schedule_data(
        file_path="resources/test_1.xlsx",
        schedule_id="240001",
        schedule_type="target",
        engine=engine,
        auto_generate_pddl=True  # this now calls generate_pddl_for_schedule with use_optimized=True by default
    )

    # ingest in-progress schedule
    ingest_schedule_data(
        file_path="resources/test_1_progress_1.xlsx",
        schedule_id="240001",
        schedule_type="in-progress",
        engine=engine
    )

    # set current in-progress date so that the agent can compare actual vs expected progress
    set_current_in_progress_date(
        engine=engine,
        schedule_id="240001",
        user_date_str="2024-02-01 08:00:00"
    )

    # confirm that pddl files were generated
    with engine.connect() as conn:
        row = conn.execute(
            select(pddl_mappings_table).where(
                pddl_mappings_table.c.schedule_id == "240001"
            )
        ).fetchone()
        assert row, "pddl mapping not found for schedule_id=240001"
        assert os.path.exists(row.domain_file), f"domain file not found: {row.domain_file}"
        assert os.path.exists(row.problem_file), f"problem file not found: {row.problem_file}"
    
    # Optionally, check that the new domain file has our new chunking constructs.
    with open(row.domain_file, "r") as f:
        domain_content = f.read()
    assert "(in-chunk" in domain_content, "Expected '(in-chunk' not found in domain file."
    assert "(chunk-order" in domain_content, "Expected '(chunk-order' not found in domain file."

    # run analysis to ensure behind/ahead tasks are identified
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress("240001")
    print("analysis result:", result)
    assert "schedule_id" in result
    assert "insights" in result
    # optional: check if there are any insights (warnings or indications of schedule deviations)
    assert result["insights"], "no schedule insights found"