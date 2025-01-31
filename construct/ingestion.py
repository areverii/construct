import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from .models import ScheduleData, ScheduleRow

def ingest_schedule_data(file_path: str, schedule_id: Optional[str] = None, schedule_type: str = "target") -> ScheduleData:
    """
    Loads an Excel file into a structured ScheduleData format without saving it back to Excel.
    """
    df = pd.read_excel(file_path)
    
    # Convert string-based IDs
    df["project_id"] = df["project_id"].astype(str)
    df["task_id"] = df["task_id"].astype(str)
    df["parent_id"] = df["parent_id"].astype(str)
    df["p6_wbs_parent_guid"] = df["p6_wbs_parent_guid"].astype(str)

    # Ensure WBS value remains a string
    df["wbs_value"] = df["wbs_value"].astype(str)
    df["task_name"] = df["task_name"].astype(str)

    # Convert date columns safely and make timezone-naive
    datetime_cols = [
        "start_date", "end_date", "bl_start", "bl_finish",
        "constraint_date", "deadline_date", "date_and_time"
    ]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[col] = df[col].dt.tz_localize(None)  # Remove timezone info

    # Convert numeric columns properly
    numeric_cols = ["percent_done", "duration", "crew_size", "deadline_variance", "ordered_parent_index", "p6_wbs_level"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert p6_wbs_level explicitly to int where possible
    df["p6_wbs_level"] = df["p6_wbs_level"].apply(lambda x: int(x) if not pd.isna(x) else None)

    # Convert NaN -> None for all fields
    df = df.replace({np.nan: None})

    # Convert rows into ScheduleRow objects
    rows = [ScheduleRow(**row) for row in df.to_dict(orient="records")]
    
    final_schedule_id = schedule_id or (rows[0].project_id if rows else "demo_schedule")

    # Return structured ScheduleData (no Excel output)
    return ScheduleData(schedule_id=final_schedule_id, tasks=rows)