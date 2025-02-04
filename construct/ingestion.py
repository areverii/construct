import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete
from construct.database import projects_table, tasks_table
from construct.models import ScheduleData
from construct.pddl_generation import generate_pddl_for_schedule

def _compute_duration_if_missing(row):
    """Compute duration from (bl_finish - bl_start) if duration is None or <= 0."""
    if row.get("duration") and row["duration"] > 0:
        # has a positive duration already
        return row["duration"]
    # try computing from baseline
    start_str = row.get("bl_start")
    finish_str = row.get("bl_finish")
    if not start_str or not finish_str:
        return None
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        finish_dt = datetime.strptime(finish_str, "%Y-%m-%d %H:%M:%S")
        if finish_dt <= start_dt:
            return None
        delta = finish_dt - start_dt
        # convert to days (or hours if you prefer)
        duration_days = delta.total_seconds() / 86400.0
        return duration_days
    except ValueError:
        return None

def ingest_schedule_data(
    file_path: str,
    schedule_id: str = None,
    schedule_type: str = None,
    engine=None,
    auto_generate_pddl: bool = True
):
    df = pd.read_excel(file_path)
    project_name = df.iloc[0].get("project_name", "Unknown") if not df.empty else "Unknown"
    
    # standardize date columns to "YYYY-MM-DD HH:MM:SS"
    datetime_cols = ["start_date", "end_date", "bl_start", "bl_finish"]
    for c in datetime_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.replace({np.nan: None})

    # upsert project row, remove old tasks
    with engine.begin() as conn:
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
                projects_table.insert(),
                {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "project_name": project_name,
                    "created_at": str(datetime.utcnow())
                }
            )
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

            if schedule_type == "target":
                # fill baseline fields if missing
                bl_start = row.get("bl_start") or row.get("start_date")
                bl_finish = row.get("bl_finish") or row.get("end_date")

                # store baseline columns
                task_dict = {
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "task_id": str(row.get("task_id")),  # ensure string
                    "task_name": row.get("task_name"),
                    "wbs_value": row.get("wbs_value"),
                    "parent_id": str(row.get("parent_id")) if row.get("parent_id") else None,
                    "p6_wbs_guid": row.get("p6_wbs_guid"),
                    "percent_done": row.get("percent_done"),
                    "bl_start": bl_start,
                    "bl_finish": bl_finish,
                    "duration": row.get("duration"),  # might be None or 0
                    "status": row.get("status"),
                }
            else:
                # in-progress => store actual columns
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
                    "duration": row.get("duration"),
                    "status": row.get("status"),
                }

            task_rows.append(task_dict)

        if task_rows:
            conn.execute(tasks_table.insert(), task_rows)

    # generate pddl if it's a target schedule
    if auto_generate_pddl and schedule_type == "target":
        try:
            # we do a second pass to compute durations for leaf tasks and skip summary tasks
            # inside 'generate_pddl_for_schedule'
            generate_pddl_for_schedule(schedule_id, engine)
        except Exception as e:
            print(f"pddl generation failed: {e}")
            raise  # re-raise so tests can see the failure

    return ScheduleData(schedule_id=schedule_id, tasks=[])