import pytest
from construct.ingestion import ingest_schedule_data
from construct.database import init_db

def test_ingest_schedule_xlsx(sample_schedule_xlsx, tmp_path):
    """
    Regression test for ingesting schedule data from an XLSX file.
    Steps:
      1. Initializes a temporary SQLite database.
      2. Ingests schedule data from the provided XLSX file.
      3. Asserts that the ingestion process returns an object with a valid schedule_id.
    """
    # Create a temporary database file.
    test_db_path = tmp_path / "ingestion_regression.db"
    engine = init_db(db_url=f"sqlite:///{test_db_path}")
    
    # Ingest the schedule data.
    result = ingest_schedule_data(str(sample_schedule_xlsx), schedule_type="target", engine=engine)
    
    # Verify results.
    assert result is not None, "Ingestion returned None."
    assert hasattr(result, 'schedule_id'), "Ingestion result missing schedule_id."