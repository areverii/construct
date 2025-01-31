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
    Ingest a schedule file and store it in the database.
    """
    engine = init_db()
    agent = ConstructionAgent(engine)

    # Ingest the Excel file and convert to structured format
    schedule_data = ingest_schedule_data(file_path, schedule_type=schedule_type)

    # Convert schedule data to JSON and store it in the database
    with engine.connect() as conn:
        conn.execute(
            schedule_table.insert(),
            {
                "name": schedule_data.schedule_id,
                "type": schedule_type,
                "raw_data": schedule_data.json()  # Store JSON representation
            }
        )

    result = agent.process_schedule(schedule_data)
    typer.echo(json.dumps(result))

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