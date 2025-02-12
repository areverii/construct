# tests/test_integration.py
import pytest
import pandas as pd
from io import BytesIO
from construct.database import init_db, pddl_mappings_table, tasks_table, dependencies_table
from construct.ingestion import ingest_schedule_data
from construct.agent import ConstructionAgent
from sqlalchemy import select

@pytest.fixture
def engine():
    # in-memory test db
    return init_db("sqlite:///:memory:")

def test_end_to_end_integration(engine):
    # create target schedule
    df_target = pd.DataFrame([
        {
            "task_id": "T1",
            "task_name": "Excavation",
            "bl_start": "2025-03-01 08:00:00",
            "bl_finish": "2025-03-05 17:00:00",
            "duration": 4
        },
        {
            "task_id": "T2",
            "task_name": "Foundation",
            "bl_start": "2025-03-06 08:00:00",
            "bl_finish": "2025-03-10 17:00:00",
            "duration": 4
        },
    ])
    bio_target = BytesIO()
    with pd.ExcelWriter(bio_target) as writer:
        df_target.to_excel(writer, index=False)
    bio_target.seek(0)

    # ingest as target
    ingest_schedule_data(
        file_path=bio_target,
        schedule_id="test_integration",
        schedule_type="target",
        engine=engine
    )

    # manually insert a dependency (T2 depends on T1)
    with engine.begin() as conn:
        conn.execute(
            dependencies_table.insert(),
            {
                "schedule_id": "test_integration",
                "task_id": "T2",
                "depends_on_task_id": "T1"
            },
        )

    # create in-progress schedule
    df_progress = pd.DataFrame([
        {
            "task_id": "T1",
            "task_name": "Excavation",
            "start_date": "2025-03-01 08:00:00",
            "end_date": None,
            "percent_done": 10.0,
        },
        {
            "task_id": "T2",
            "task_name": "Foundation",
            "start_date": None,
            "end_date": None,
            "percent_done": 0.0,
        },
    ])
    bio_progress = BytesIO()
    with pd.ExcelWriter(bio_progress) as writer:
        df_progress.to_excel(writer, index=False)
    bio_progress.seek(0)

    # ingest as in-progress
    ingest_schedule_data(
        file_path=bio_progress,
        schedule_id="test_integration",
        schedule_type="in-progress",
        engine=engine
    )

    # check pddl mapping
    with engine.connect() as conn:
        row = conn.execute(
            select(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "test_integration")
        ).fetchone()
        assert row, "pddl mapping not found"
        assert row.domain_file and row.problem_file

    # run agent analysis
    agent = ConstructionAgent(engine)
    analysis = agent.analyze_progress("test_integration")
    print(analysis)

    # we expect T1 to be behind schedule
    assert "behind schedule" in " ".join(analysis.get("insights", [])), "T1 should be behind schedule"