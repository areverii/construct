# construct/database.py

import os
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, Float

metadata = MetaData()
gen_folder = "gen"
os.makedirs(gen_folder, exist_ok=True)

projects_table = Table(
    "projects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String),
    Column("schedule_type", String),  # "target" or "in-progress"
    Column("project_name", String),
    Column("created_at", String),
    Column("project_start_date", String, nullable=True),
    Column("project_end_date", String, nullable=True),
    Column("current_in_progress_date", String, nullable=True),
)

tasks_table = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String, ForeignKey("projects.schedule_id")),
    Column("schedule_type", String),  # "target" or "in-progress"
    Column("task_id", String),
    Column("task_name", String),
    Column("wbs_value", String),
    Column("parent_id", String),
    Column("p6_wbs_guid", String),
    Column("percent_done", Float),

    # baseline columns (for target schedule)
    Column("bl_start", String),   # e.g. "1/27/2020 7:00"
    Column("bl_finish", String),  # e.g. "5/30/2025 17:00"

    # actual / forecast columns (for in-progress schedule)
    Column("start_date", String),
    Column("end_date", String),

    Column("duration", Float),
    Column("status", String)
)

dependencies_table = Table(
    "dependencies",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String, ForeignKey("projects.schedule_id")),
    Column("task_id", String, ForeignKey("tasks.task_id")),
    Column("depends_on_task_id", String, ForeignKey("tasks.task_id"))
)

def init_db(db_url: str = None):
    if not db_url:
        db_path = os.path.abspath(os.path.join(gen_folder, "construct.db"))
        db_url = f"sqlite:///{db_path}"
    print(f"debug: initializing db at {db_url}")
    engine = create_engine(db_url, echo=True)
    metadata.create_all(engine)
    return engine