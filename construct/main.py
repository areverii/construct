# construct/main.py

import os
import json
import typer
from sqlalchemy import select
from datetime import datetime
from construct.database import init_db, projects_table
from construct.ingestion import ingest_schedule_data
from construct.agent import ConstructionAgent

app = typer.Typer()

@app.command("ingest-schedule")
def ingest_schedule_cli(
    file_path: str,
    schedule_type: str = typer.Option("target", help="Type of schedule: 'target' or 'in-progress'")
):
    engine = init_db()
    # simply call ingest_schedule_data with no double insert
    schedule_data = ingest_schedule_data(file_path, schedule_type=schedule_type, engine=engine)

    if schedule_data is None:
        print("ERROR: schedule_data is None. Exiting.")
        return

    print(f"DEBUG: Finished ingestion for schedule_id={schedule_data.schedule_id} ({schedule_type}).")

@app.command("compare-schedules")
def compare_schedules_cli(schedule_id: str):
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)
    typer.echo(json.dumps(result, indent=2))

def main():
    app()

if __name__ == "__main__":
    main()