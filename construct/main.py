import os
import json
import typer
from dotenv import load_dotenv
load_dotenv()

from construct.project import create_project
from construct.database import init_db
from construct.ingestion import ingest_schedule_data, update_task_progress
from construct.project_management import set_current_in_progress_date
from construct.agent import ConstructionAgent
from construct.llm_agent import run_llm_agent

app = typer.Typer()

@app.command("create-project")
def create_project_cli(
    cproj_path: str,
    project_name: str,
    schedule_id: str,
    db_url: str = None
):
    engine, proj_info = create_project(cproj_path, project_name, schedule_id, db_url)
    typer.echo(f"Project created: {proj_info}")
    typer.echo(f"DB initialized at: {engine.url}")

@app.command("ingest-schedule")
def ingest_schedule_cli(
    file_path: str,
    schedule_id: str,
    schedule_type: str = typer.Option("target", help="Schedule type: 'target' or 'in-progress'")
):
    engine = init_db()  # uses default DB URL unless overridden
    ingest_schedule_data(file_path, schedule_id, schedule_type, engine, auto_generate_pddl=True)
    typer.echo(f"Finished ingestion for schedule {schedule_id} ({schedule_type}).")

@app.command("update-task")
def update_task_cli(
    schedule_id: str,
    task_id: str,
    percent_done: float
):
    engine = init_db()
    update_task_progress(engine, schedule_id, task_id, percent_done)
    typer.echo(f"Updated task {task_id} for schedule {schedule_id} to {percent_done}%.")

@app.command("set-in-progress-date")
def set_in_progress_date_cli(
    schedule_id: str,
    user_date_str: str
):
    engine = init_db()
    set_current_in_progress_date(engine, schedule_id, user_date_str)
    typer.echo(f"Set current in-progress date for {schedule_id} to {user_date_str}.")

@app.command("compare-schedules")
def compare_schedules_cli(schedule_id: str):
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)
    typer.echo(json.dumps(result, indent=2))

@app.command("agent-analyze")
def agent_analyze_cli(schedule_id: str, prompt: str):
    result = run_llm_agent(schedule_id, prompt)
    typer.echo("\nLLM Analysis:\n" + result)

def main():
    app()

if __name__ == "__main__":
    main()