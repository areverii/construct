from fastapi import FastAPI
from construct.database import init_db
from construct.ingestion import ingest_schedule_data
from construct.agent import ConstructionAgent
from construct.llm_agent import run_llm_agent
from construct.scheduler import run_optic

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to the Construction API"}

@app.post("/ingest-schedule/")
def ingest_schedule(file_path: str, schedule_type: str = "target"):
    engine = init_db()
    schedule_data = ingest_schedule_data(file_path, schedule_type=schedule_type, engine=engine)
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