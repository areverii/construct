import pytest
from construct.database import init_db, pddl_mappings_table
from construct.ingestion import ingest_schedule_data
from sqlalchemy import select
import pandas as pd
from io import BytesIO

@pytest.fixture
def engine():
    return init_db("sqlite:///:memory:")

def test_pddl_generation_valid(engine):
    # create a small in-memory df
    df = pd.DataFrame([{
        "task_id": "T1", "task_name": "Task1",
        "bl_start": "2025-01-01 08:00:00", "bl_finish": "2025-01-05 17:00:00",
        "duration": 4
    }])
    bio = BytesIO()
    with pd.ExcelWriter(bio) as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)

    ingest_schedule_data(file_path=bio, schedule_id="test001", schedule_type="target", engine=engine)

    # check if mapping was created
    with engine.connect() as conn:
        row = conn.execute(select(pddl_mappings_table)).fetchone()
        assert row is not None
        assert "test001" in row.schedule_id
        assert row.domain_file and row.problem_file

def test_pddl_generation_missing_dates(engine):
    df = pd.DataFrame([{
        "task_id": "T1", "task_name": "NoDates",
        "duration": 5
    }])
    bio = BytesIO()
    with pd.ExcelWriter(bio) as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)

    # expect validation error
    with pytest.raises(Exception):
        ingest_schedule_data(file_path=bio, schedule_id="bad001", schedule_type="target", engine=engine)
