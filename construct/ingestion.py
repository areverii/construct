import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from .models import ScheduleData, ScheduleRow
from construct.database import projects_table, tasks_table, dependencies_table
from sqlalchemy import insert

def ingest_schedule_data(file_path: str, schedule_id: Optional[str] = None, schedule_type: str = "target", engine=None):
    """
    Ingests an Excel schedule file into the structured DB format.
    Requires an active SQLAlchemy engine.
    """
    if engine is None:
        raise ValueError("Database engine must be provided.")

    print(f"DEBUG: Loading {file_path}")

    df = pd.read_excel(file_path)

    # Extract schedule_id and ensure it is a STRING
    inferred_schedule_id = str(df["project_id"].iloc[0]) if "project_id" in df.columns and not df["project_id"].isna().all() else None
    schedule_id = str(schedule_id or inferred_schedule_id)  # Convert to string

    if schedule_id is None:
        raise ValueError("Could not determine schedule_id. Ensure 'project_id' column exists in the Excel file.")

    print(f"DEBUG: Ingesting schedule {schedule_id} as {schedule_type} (type: {type(schedule_id)})")  # Debugging output

    # Convert dates
    datetime_cols = ["start_date", "end_date"]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    # Convert NaN -> None
    df = df.replace({np.nan: None})

    # ✅ Insert into DB
    with engine.connect() as conn:
        try:
            conn.execute(
                projects_table.insert(),
                {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "project_name": df.iloc[0].get("project_name", "Unknown"),
                    "created_at": str(datetime.utcnow())
                }
            )

            for _, row in df.iterrows():
                conn.execute(
                    tasks_table.insert(),
                    {
                        "schedule_id": schedule_id,  # ✅ Ensure this is a string
                        "task_id": row["task_id"],
                        "task_name": row["task_name"],
                        "wbs_value": row["wbs_value"],
                        "parent_id": row["parent_id"],
                        "p6_wbs_guid": row["p6_wbs_guid"],
                        "percent_done": row["percent_done"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                        "duration": row["duration"],
                        "status": None
                    }
                )

            print(f"DEBUG: Committing transaction for schedule {schedule_id}")
            conn.commit()  # ✅ Explicitly commit the transaction

            print(f"DEBUG: Successfully ingested schedule {schedule_id} ({schedule_type})")
            return ScheduleData(schedule_id=schedule_id, tasks=[])
        
        except Exception as e:
            print(f"ERROR: Database insertion failed: {e}")  # ✅ Print exact error message
            conn.rollback()
            return None