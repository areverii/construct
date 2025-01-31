import os
import json
import typer
from construct.database import init_db, schedule_table
from construct.ingestion import ingest_schedule_data
from construct.pddl_utils import schedule_to_pddl, save_pddl
from construct.agent import ConstructionAgent

app = typer.Typer()

@app.command("ingest-schedule")
def ingest_schedule_cli(file_path: str, schedule_type: str = typer.Option("target", help="Type of schedule: 'target' or 'in-progress'")):
    """
    Ingest a schedule file and process it.
    """
    engine = init_db()
    agent = ConstructionAgent(engine)

    schedule_data = ingest_schedule_data(file_path, schedule_type=schedule_type)

    print(f"DEBUG: Storing schedule {schedule_data.schedule_id} as {schedule_type}")

    # Store in DB with explicit COMMIT
    with engine.connect() as conn:
        conn.execute(
            schedule_table.insert(),
            {
                "name": schedule_data.schedule_id,
                "type": schedule_type,
                "raw_data": schedule_data.json()
            }
        )
        conn.commit()  # Explicitly commit the transaction

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