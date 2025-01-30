# construct/database.py

import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

metadata = MetaData()

schedule_table = Table(
    "schedules",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("raw_data", String),
)

def init_db(db_url: str = "sqlite:///construct.db"):
    engine = create_engine(db_url)
    metadata.create_all(engine)
    return engine