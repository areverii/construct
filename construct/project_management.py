# construct/project_management.py
import datetime
from sqlalchemy import update
from construct.database import projects_table
from typing import Optional

def try_parse_datetime(date_str: str) -> Optional[str]:
    """
    Accept common user-supplied formats, parse to a datetime object,
    then return the 'YYYY-MM-DD HH:MM:SS' string for DB storage.
    """
    # possible user input formats
    formats = [
        "%Y-%m-%d",             # '2023-09-07'
        "%Y-%m-%d %H:%M:%S",    # '2023-09-07 08:00:00'
        "%m/%d/%Y %H:%M:%S %p", # '9/7/2023 8:00:00 AM'
        "%m/%d/%Y %I:%M:%S %p", # same as above, sometimes %I used
        "%m/%d/%Y",             # '9/7/2023' (no time)
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            # normalize to ISO-like: 'YYYY-MM-DD HH:MM:SS'
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    raise ValueError(f"Could not parse date/time: {date_str}")

def set_project_start_date(engine, schedule_id: str, user_date_str: str):
    iso_date = try_parse_datetime(user_date_str)
    with engine.connect() as conn:
        conn.execute(
            update(projects_table)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == "target")
            .values(project_start_date=iso_date)
        )
        conn.commit()
    print(f"DEBUG: Project start date for {schedule_id} set to {iso_date}")

def set_project_end_date(engine, schedule_id: str, user_date_str: str):
    iso_date = try_parse_datetime(user_date_str)
    with engine.connect() as conn:
        conn.execute(
            update(projects_table)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == "target")
            .values(project_end_date=iso_date)
        )
        conn.commit()
    print(f"DEBUG: Project end date for {schedule_id} set to {iso_date}")

def set_current_in_progress_date(engine, schedule_id: str, user_date_str: str):
    iso_date = try_parse_datetime(user_date_str)
    with engine.connect() as conn:
        conn.execute(
            update(projects_table)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == "in-progress")
            .values(current_in_progress_date=iso_date)
        )
        conn.commit()
    print(f"DEBUG: Current in-progress date for {schedule_id} set to {iso_date}")