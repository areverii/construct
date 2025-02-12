from fastapi import FastAPI
from construct.database import init_db
from construct.ingestion import ingest_schedule_data
from construct.agent import ConstructionAgent
from construct.llm_agent import run_llm_agent
from construct.scheduler import run_optic
import json
from fastapi import HTTPException, Body
from pydantic import BaseModel
from construct.project import create_project
import os
from sqlalchemy import text

app = FastAPI()

class CreateProjectRequest(BaseModel):
    project_name: str
    schedule_id: str
    project_folder: str

@app.post("/create-project/")
def create_project_endpoint(request: CreateProjectRequest):
    safe_name = request.project_name.replace(" ", "_")
    folder = os.path.join(request.project_folder, safe_name)
    os.makedirs(folder, exist_ok=True)
    project_file, db_file = create_project(request.project_name, request.schedule_id, folder)
    engine = init_db(db_url=f"sqlite:///{db_file}")
    # Return absolute paths for consistency.
    return {
        "message": "Project created successfully",
        "project_file": os.path.abspath(project_file),
        "db_file": os.path.abspath(db_file)
    }

@app.post("/ingest-schedule/")
def ingest_schedule(file_path: str, schedule_id: str, schedule_type: str = "target", project_handle: str = None):
    if project_handle:
        try:
            # Ensure the project handle is an absolute path.
            if not os.path.isabs(project_handle):
                project_handle = os.path.abspath(project_handle)
            with open(project_handle, "r") as f:
                project_data = json.load(f)
            db_file = project_data.get("db_file")
            project_folder = project_data.get("project_folder")
            if not db_file or not project_folder:
                raise HTTPException(status_code=400, detail="Invalid project handle: missing db_file or project_folder")
            engine = init_db(db_url=f"sqlite:///{db_file}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not open project handle: {e}")
    else:
        engine = init_db()
        project_folder = None

    # Pass the project_folder to the ingestion function so that generated PDDL files are written there.
    schedule_data = ingest_schedule_data(
        file_path,
        schedule_id,
        schedule_type=schedule_type,
        engine=engine,
        auto_generate_pddl=True,
        project_folder=project_folder
    )
    if schedule_data is None:
        return {"error": "Failed to ingest schedule"}
    return {"status": "success", "schedule_id": schedule_data.schedule_id}

@app.get("/compare-schedules/{schedule_id}")
def compare_schedules(schedule_id: str):
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)
    return {"schedule_id": schedule_id, "analysis": result}

@app.post("/agent-analyze/")
def agent_analyze(schedule_id: str, prompt: str):
    result = run_llm_agent(schedule_id, prompt)
    return {"schedule_id": schedule_id, "analysis": result}

@app.post("/run-scheduler/")
def run_scheduler(schedule_id: str):
    engine = init_db()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM pddl_mappings WHERE schedule_id = :schedule_id"),
            {"schedule_id": schedule_id}
        ).fetchone()
    if row is None:
        return {"error": f"No PDDL mapping found for schedule {schedule_id}"}
    
    mapping = row._mapping
    result = run_optic(mapping["domain_file"], mapping["problem_file"])
    return {"status": "success", "result": result}