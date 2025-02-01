# construct/ingestion.py

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import select, update, delete
from construct.database import projects_table, tasks_table
from construct.models import ScheduleData

def ingest_schedule_data(file_path: str, schedule_id: str, schedule_type: str, engine):
    df = pd.read_excel(file_path)

    # parse out project name if present, or fallback
    project_name = df.iloc[0].get("project_name", "Unknown") if not df.empty else "Unknown"

    # standard columns for date/time
    # adapt to your actual excel columns if they're named differently
    datetime_cols = ["start_date", "end_date", "bl_start", "bl_finish"]
    for c in datetime_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    # handle missing values
    df = df.replace({np.nan: None})

    with engine.begin() as conn:
        # upsert project row
        existing = conn.execute(
            select(projects_table.c.id)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == schedule_type)
        ).fetchone()

        if existing:
            # update if needed
            conn.execute(
                update(projects_table)
                .where(projects_table.c.schedule_id == schedule_id)
                .where(projects_table.c.schedule_type == schedule_type)
                .values(project_name=project_name)
            )
        else:
            # insert if not found
            conn.execute(projects_table.insert(), {
                "schedule_id": schedule_id,
                "schedule_type": schedule_type,
                "project_name": project_name,
                "created_at": str(datetime.utcnow())
            })

        # remove old tasks for that schedule
        conn.execute(
            delete(tasks_table)
            .where(tasks_table.c.schedule_id == schedule_id)
            .where(tasks_table.c.schedule_type == schedule_type)
        )

        # build list of rows to insert
        task_rows = []
        for _, row in df.iterrows():
            if not row.get("task_id"):
                continue

            # for target schedules, store to baseline columns
            if schedule_type == "target":
                task_rows.append({
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "task_id": row.get("task_id"),
                    "task_name": row.get("task_name"),
                    "wbs_value": row.get("wbs_value"),
                    "parent_id": row.get("parent_id"),
                    "p6_wbs_guid": row.get("p6_wbs_guid"),
                    "percent_done": row.get("percent_done"),
                    # store baseline columns
                    "bl_start": row.get("bl_start") or row.get("start_date"),
                    "bl_finish": row.get("bl_finish") or row.get("end_date"),
                    "duration": row.get("duration"),
                    "status": row.get("status"),
                })
            else:
                # in-progress => store actual columns
                task_rows.append({
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "task_id": row.get("task_id"),
                    "task_name": row.get("task_name"),
                    "wbs_value": row.get("wbs_value"),
                    "parent_id": row.get("parent_id"),
                    "p6_wbs_guid": row.get("p6_wbs_guid"),
                    "percent_done": row.get("percent_done"),
                    # store actual columns
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                    "duration": row.get("duration"),
                    "status": row.get("status"),
                })

        if task_rows:
            conn.execute(tasks_table.insert(), task_rows)

    return ScheduleData(schedule_id=schedule_id, tasks=[])