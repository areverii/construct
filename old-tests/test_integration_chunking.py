# tests/test_integration_chunking.py
import os
import re
import pytest
from sqlalchemy import select
from construct.database import init_db, pddl_mappings_table
from construct.ingestion import ingest_schedule_data
from construct.project_management import set_current_in_progress_date
from construct.agent import ConstructionAgent

TEST_DB_PATH = "gen/construct_test_integration.db"

@pytest.mark.order(1)
def test_full_integration_chunking():
    # Remove any leftover test DB file.
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Initialize a fresh engine for this test DB.
    engine = init_db(db_url=f"sqlite:///{TEST_DB_PATH}")

    # Ingest the target schedule and trigger extended (chunked) PDDL generation.
    ingest_schedule_data(
        file_path="resources/test_1.xlsx",
        schedule_id="240001",
        schedule_type="target",
        engine=engine,
        auto_generate_pddl=True  # triggers extended PDDL generation with chunking
    )

    # Ingest the in-progress schedule.
    ingest_schedule_data(
        file_path="resources/test_1_progress_1.xlsx",
        schedule_id="240001",
        schedule_type="in-progress",
        engine=engine
    )

    # Set the current in-progress date so that progress can be analyzed.
    set_current_in_progress_date(
        engine=engine,
        schedule_id="240001",
        user_date_str="2024-02-01 08:00:00"  # from the README example
    )

    # Confirm that a PDDL mapping was inserted and that the corresponding files exist.
    with engine.connect() as conn:
        mapping_row = conn.execute(
            select(pddl_mappings_table).where(
                pddl_mappings_table.c.schedule_id == "240001"
            )
        ).fetchone()
    assert mapping_row is not None, "PDDL mapping not found for schedule_id=240001"
    domain_file = mapping_row.domain_file
    problem_file = mapping_row.problem_file
    assert os.path.exists(domain_file), f"Domain file not found: {domain_file}"
    assert os.path.exists(problem_file), f"Problem file not found: {problem_file}"

    # Load and validate the domain file.
    with open(domain_file, "r") as f:
        domain_contents = f.read()

    # Check that the domain declares both types.
    assert "(:types task chunk)" in domain_contents, "Missing types declaration for task and chunk"

    # Check that the new predicates are declared.
    for predicate in [
        "(done ?t - task)",
        "(in-chunk ?t - task ?c - chunk)",
        "(chunk-order ?c1 - chunk ?c2 - chunk)"
    ]:
        assert predicate in domain_contents, f"Missing predicate declaration: {predicate}"

    # (Optionally) Count the number of durative actions.
    num_actions = domain_contents.count("(:durative-action")
    assert num_actions > 10, f"Expected a large number of actions in domain, found {num_actions}"

    # Check that at least one action has a computed duration different from a default minimal value (e.g. 1.0)
    duration_matches = re.findall(r":duration \(= \?duration ([\d\.]+)\)", domain_contents)
    durations = []
    for d in duration_matches:
        try:
            durations.append(float(d))
        except ValueError:
            pass
    assert any(d != 1.0 for d in durations), "Expected some computed durations different from 1.0"

    # Load and validate the problem file.
    with open(problem_file, "r") as f:
        problem_contents = f.read()

    # Instead of checking for "t_T", we now check that the objects section declares some tasks and chunks.
    # Look for the dash markers that indicate types.
    assert "- task" in problem_contents, "No task objects found in problem file"
    assert "- chunk" in problem_contents, "No chunk objects found in problem file"
    # And that there is a chunk-order predicate somewhere in the problem.
    assert "chunk-order" in problem_contents, "Missing chunk-order information in problem file"

    # Run agent analysis to ensure schedule insights are produced.
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress("240001")
    print("Agent analysis result:", result)
    assert "schedule_id" in result, "Agent analysis missing schedule_id"
    assert "insights" in result, "Agent analysis missing insights"
    assert result["insights"], "No schedule insights found"