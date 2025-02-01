# construct/ingestion.py

import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from .models import ScheduleData, ScheduleRow
from construct.database import projects_table, tasks_table, dependencies_table
from sqlalchemy import insert, select, update, delete

def ingest_schedule_data(
    file_path: str,
    schedule_id: Optional[str] = None,
    schedule_type: str = "target",
    engine=None
):
    if engine is None:
        raise ValueError("Database engine must be provided.")

    print(f"DEBUG: Loading {file_path}")
    df = pd.read_excel(file_path)

    # get schedule_id from CLI arg or from xlsx "project_id"
    inferred_schedule_id = None
    if "project_id" in df.columns and not df["project_id"].isna().all():
        inferred_schedule_id = str(df["project_id"].iloc[0])

    schedule_id = str(schedule_id or inferred_schedule_id)
    if not schedule_id or schedule_id.strip() == "":
        raise ValueError("ERROR: schedule_id is missing or corrupt. Check Excel file.")

    print(f"DEBUG: Ingesting schedule {schedule_id} as {schedule_type}")

    # parse date columns
    datetime_cols = ["start_date", "end_date"]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    df = df.replace({np.nan: None})

    with engine.connect() as conn:
        existing = conn.execute(
            select(projects_table.c.schedule_id)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == schedule_type)
        ).fetchone()

        if existing:
            print(f"DEBUG: Schedule {schedule_id} ({schedule_type}) exists. Updating project info if needed.")
            if schedule_type == "target":
                start_date = df.iloc[0].get("start_date", None)
                end_date = df.iloc[0].get("end_date", None)
                conn.execute(
                    update(projects_table)
                    .where(projects_table.c.schedule_id == schedule_id)
                    .where(projects_table.c.schedule_type == schedule_type)
                    .values(
                        project_start_date=start_date,
                        project_end_date=end_date
                    )
                )
            else:
                # in-progress
                conn.execute(
                    update(projects_table)
                    .where(projects_table.c.schedule_id == schedule_id)
                    .where(projects_table.c.schedule_type == schedule_type)
                    .values(
                        current_in_progress_date=str(datetime.utcnow().date())
                    )
                )
            conn.commit()
        else:
            print(f"DEBUG: Inserting new schedule {schedule_id} ({schedule_type})")
            project_start_date = df.iloc[0].get("start_date", None) if schedule_type == "target" else None
            project_end_date = df.iloc[0].get("end_date", None) if schedule_type == "target" else None
            current_in_progress_date = str(datetime.utcnow().date()) if schedule_type == "in-progress" else None

            conn.execute(
                projects_table.insert(),
                {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "project_name": df.iloc[0].get("project_name", "Unknown"),
                    "created_at": str(datetime.utcnow()),
                    "project_start_date": project_start_date,
                    "project_end_date": project_end_date,
                    "current_in_progress_date": current_in_progress_date
                }
            )
            conn.commit()

        # now insert or update tasks
        task_rows = []
        for _, row in df.iterrows():
            # skip rows missing a task_id or similar, if needed
            if not row.get("task_id"):
                continue

            task_row = {
                "schedule_id": schedule_id,
                "schedule_type": schedule_type,
                "task_id": row.get("task_id"),
                "task_name": row.get("task_name"),
                "wbs_value": row.get("wbs_value"),
                "parent_id": row.get("parent_id"),
                "p6_wbs_guid": row.get("p6_wbs_guid"),
                "percent_done": row.get("percent_done"),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "duration": row.get("duration"),
                "status": row.get("status")
            }
            task_rows.append(task_row)

        # for a simple approach, delete existing tasks for (schedule_id, schedule_type) then re-insert
        conn.execute(
            delete(tasks_table)
            .where(tasks_table.c.schedule_id == schedule_id)
            .where(tasks_table.c.schedule_type == schedule_type)
        )
        conn.commit()

        if task_rows:
            conn.execute(tasks_table.insert(), task_rows)
            conn.commit()

        print(f"DEBUG: Inserted {len(task_rows)} tasks for schedule {schedule_id} ({schedule_type}).")

    return ScheduleData(schedule_id=schedule_id, tasks=[])