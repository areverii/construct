import os
import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

metadata = MetaData()

# Ensure generated folder exists
GENERATED_FOLDER = "gen"
os.makedirs(GENERATED_FOLDER, exist_ok=True)

schedule_table = Table(
    "schedules",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, unique=True),
    Column("type", String),  # "target" or "in-progress"
    Column("raw_data", String),  # JSON serialized schedule data
)

def init_db(db_url: str = f"sqlite:///{GENERATED_FOLDER}/construct.db"):
    engine = create_engine(db_url)
    metadata.create_all(engine)
    return engine