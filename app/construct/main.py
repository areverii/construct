# construct/main.py
import os
import json
import typer
from dotenv import load_dotenv
load_dotenv()

from construct.database import init_db, pddl_mappings_table
from construct.ingestion import ingest_schedule_data
from construct.project_management import set_current_in_progress_date
from construct.agent import ConstructionAgent
from construct.llm_agent import run_llm_agent
from construct.scheduler import run_optic
from sqlalchemy import text

app = typer.Typer()

@app.command("ingest-schedule")
def ingest_schedule_cli(
    file_path: str,
    schedule_type: str = typer.Option("target", help="Type of schedule: 'target' or 'in-progress'")
):
    engine = init_db()
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

@app.command("agent-analyze")
def agent_analyze_cli(schedule_id: str, prompt: str = typer.Argument(...)):
    result = run_llm_agent(schedule_id, prompt)
    print("\nLLM Analysis:\n", result)

@app.command("run-scheduler")
def run_scheduler_cli(schedule_id: str):
    """
    Runs the OPTIC scheduler on the current PDDL files for the given schedule.
    """
    engine = init_db()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM pddl_mappings WHERE schedule_id = :schedule_id"),
            {"schedule_id": schedule_id}
        ).fetchone()
    if row is None:
        typer.echo(f"No PDDL mapping found for schedule {schedule_id}")
        raise typer.Exit(code=1)
    # Use the row’s _mapping attribute for string-key access.
    mapping = row._mapping
    domain_file = mapping["domain_file"]
    problem_file = mapping["problem_file"]
    result = run_optic(domain_file, problem_file)
    typer.echo(result)

@app.command("run-api")
def run_api():
    print("Starting API...")
    # Here you would start a FastAPI/Flask server if needed

def main():
    app()

if __name__ == "__main__":
    main()