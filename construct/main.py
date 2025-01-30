
# construct/main.py

import json
import typer
from construct.database import init_db, schedule_table
from construct.ingestion import ingest_schedule_data
from construct.pddl_utils import schedule_to_pddl, save_pddl
from construct.agent import ConstructionAgent

app = typer.Typer()

@app.command("ingest-schedule")
def ingest_schedule_cli(file_path: str):
    """
    Ingest a schedule file and process it.
    """
    engine = init_db()
    agent = ConstructionAgent()

    schedule_data = ingest_schedule_data(file_path)
    domain_str, problem_str = schedule_to_pddl(schedule_data)
    save_pddl(domain_str, problem_str, base_name=schedule_data.schedule_id)

    # store in db as json
    with engine.connect() as conn:
        conn.execute(
            schedule_table.insert(),
            {
                "name": schedule_data.schedule_id,
                "raw_data": schedule_data.json()
            }
        )

    result = agent.process_schedule(schedule_data)
    # typer.echo(json.dumps(result))

@app.command("optimize-schedule")
def optimize_schedule_cli(schedule_id: str = typer.Argument(..., help="ID of the schedule to optimize.")):
    return

def main():
    app()

if __name__ == "__main__":
    app()
