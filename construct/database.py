import os
import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, Float, Boolean, Text

metadata = MetaData()

GEN_FOLDER = "gen"
os.makedirs(GEN_FOLDER, exist_ok=True)

# Projects table stores schedule metadata (Target & In-Progress)
projects_table = Table(
    "projects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String),
    Column("schedule_type", String),  # "target" or "in-progress"
    Column("project_name", String),
    Column("created_at", String)  # Timestamp when schedule was loaded
)

# Tasks table stores hierarchical tasks
tasks_table = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String, ForeignKey("projects.schedule_id")),
    Column("task_id", String),  # Unique ID for the task
    Column("task_name", String),
    Column("wbs_value", String),  # Work Breakdown Structure (hierarchical)
    Column("parent_id", String),  # Parent task (if part of hierarchy)
    Column("p6_wbs_guid", String),  # GUID for referencing in P6
    Column("percent_done", Float),  # Progress tracking
    Column("start_date", String),
    Column("end_date", String),
    Column("duration", Float),
    Column("status", String)  # Derived: "On Track", "Delayed", "Ahead"
)

# Dependencies table tracks task relationships
dependencies_table = Table(
    "dependencies",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("schedule_id", String, ForeignKey("projects.schedule_id")),
    Column("task_id", String, ForeignKey("tasks.task_id")),
    Column("depends_on_task_id", String, ForeignKey("tasks.task_id"))  # Predecessor
)

def init_db(db_url: str = f"sqlite:///{GEN_FOLDER}/construct.db"):
    print(f"DEBUG: Initializing database at {GEN_FOLDER}/construct.db")
    engine = create_engine(db_url, echo=True)  # Enable SQL query logging
    metadata.create_all(engine)
    return engine