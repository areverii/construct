import os
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import select, update, delete, insert
from construct.database import projects_table, tasks_table, pddl_mappings_table, events_table
from construct.models import ScheduleData
from construct.pddl_generation import generate_pddl_for_schedule

def _compute_duration_if_missing(row):
    if row.get("duration") and row["duration"] > 0:
        return row["duration"]
    start_str = row.get("bl_start")
    finish_str = row.get("bl_finish")
    if not start_str or not finish_str:
        return None
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        finish_dt = datetime.strptime(finish_str, "%Y-%m-%d %H:%M:%S")
        delta = finish_dt - start_dt
        duration_days = delta.total_seconds() / 86400.0
        return duration_days
    except ValueError:
        return None

def ingest_schedule_data(
    file_path: str,
    schedule_id: str,
    schedule_type: str,
    engine,
    auto_generate_pddl: bool = True,
    project_folder: str = None
):
    df = pd.read_excel(file_path)
    project_name = df.iloc[0].get("project_name", "Unknown") if not df.empty else "Unknown"
    
    # Process datetime columns.
    datetime_cols = ["start_date", "end_date", "bl_start", "bl_finish"]
    for c in datetime_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.replace({np.nan: None})
    
    with engine.begin() as conn:
        # Upsert project record.
        existing = conn.execute(
            select(projects_table.c.id)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == schedule_type)
        ).fetchone()
        if existing:
            conn.execute(
                update(projects_table)
                .where(projects_table.c.schedule_id == schedule_id)
                .where(projects_table.c.schedule_type == schedule_type)
                .values(project_name=project_name)
            )
        else:
            conn.execute(
                insert(projects_table),
                {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "project_name": project_name,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        # Remove old tasks.
        conn.execute(
            delete(tasks_table)
            .where(tasks_table.c.schedule_id == schedule_id)
            .where(tasks_table.c.schedule_type == schedule_type)
        )
    
        # Insert tasks from the Excel rows.
        task_rows = []
        for _, row in df.iterrows():
            if not row.get("task_id"):
                continue
            if schedule_type == "target":
                bl_start = row.get("bl_start") or row.get("start_date")
                bl_finish = row.get("bl_finish") or row.get("end_date")
                task_dict = {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "task_id": str(row.get("task_id")),
                    "task_name": row.get("task_name"),
                    "wbs_value": row.get("wbs_value"),
                    "parent_id": str(row.get("parent_id")) if row.get("parent_id") else None,
                    "p6_wbs_guid": row.get("p6_wbs_guid"),
                    "percent_done": row.get("percent_done"),
                    "bl_start": bl_start,
                    "bl_finish": bl_finish,
                    "duration": row.get("duration") or _compute_duration_if_missing(row),
                    "status": row.get("status"),
                }
            else:
                task_dict = {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "task_id": str(row.get("task_id")),
                    "task_name": row.get("task_name"),
                    "wbs_value": row.get("wbs_value"),
                    "parent_id": str(row.get("parent_id")) if row.get("parent_id") else None,
                    "p6_wbs_guid": row.get("p6_wbs_guid"),
                    "percent_done": row.get("percent_done"),
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                    "duration": row.get("duration") or _compute_duration_if_missing(row),
                    "status": row.get("status"),
                }
            task_rows.append(task_dict)
    
        if task_rows:
            conn.execute(tasks_table.insert(), task_rows)
        
        # Log an event for in-progress ingestions.
        if schedule_type == "in-progress":
            conn.execute(
                insert(events_table),
                {
                    "schedule_id": schedule_id,
                    "event_type": "in_progress_ingestion",
                    "event_details": f"Ingested {len(task_rows)} tasks from {file_path}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    # Generate PDDL if applicable.
    if auto_generate_pddl and schedule_type == "target":
        generate_pddl_for_schedule(schedule_id, engine, output_dir=project_folder)
    
    return ScheduleData(schedule_id=schedule_id, tasks=[])