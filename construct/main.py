import os
import json
import typer
from sqlalchemy import select
from datetime import datetime
from construct.database import init_db, projects_table, tasks_table
from construct.ingestion import ingest_schedule_data
from construct.pddl_utils import schedule_to_pddl, save_pddl
from construct.agent import ConstructionAgent

app = typer.Typer()
@app.command("ingest-schedule")
def ingest_schedule_cli(file_path: str, schedule_type: str = typer.Option("target", help="Type of schedule: 'target' or 'in-progress'")):
    """
    Ingest a schedule file and store it in the database.
    """
    engine = init_db()
    agent = ConstructionAgent(engine)

    print(f"DEBUG: Checking if schedule {file_path} ({schedule_type}) already exists before ingestion.")

    with engine.connect() as conn:
        existing = conn.execute(
            select(projects_table.c.schedule_id)
            .where(projects_table.c.schedule_id == file_path)  # ensure correct check
            .where(projects_table.c.schedule_type == schedule_type)
        ).fetchone()

        if existing:
            print(f"DEBUG: Schedule {file_path} ({schedule_type}) already exists. Skipping ingestion.")
            return  # now it exits before doing any work

    # now call ingestion only if schedule is missing
    schedule_data = ingest_schedule_data(file_path, schedule_type=schedule_type, engine=engine)

    if schedule_data is None:
        print("ERROR: Schedule data is None. Exiting ingestion.")
        return

    print(f"DEBUG: Inserting schedule {schedule_data.schedule_id} into the database.")

    with engine.connect() as conn:
        conn.execute(
            projects_table.insert(),
            {
                "schedule_id": schedule_data.schedule_id,
                "schedule_type": schedule_type,
                "project_name": schedule_data.tasks[0].project_name if schedule_data.tasks else "Unknown",
                "created_at": str(datetime.utcnow())
            }
        )
        conn.commit()  # explicitly commit after inserting

    print(f"DEBUG: Successfully stored {schedule_data.schedule_id} ({schedule_type}) in DB")


@app.command("compare-schedules")
def compare_schedules_cli(schedule_id: str):
    """
    Compare the target schedule with the in-progress schedule and generate insights.
    """
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)
    typer.echo(json.dumps(result, indent=2))

def main():
    app()

if __name__ == "__main__":
    app()