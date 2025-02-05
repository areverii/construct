import json
import time
import threading
from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, MetaData
from construct.database import init_db, analysis_history_table
from construct.agent import ConstructionAgent
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

metadata = MetaData()

# --- Token Bucket Implementation for Rate Limiting ---
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now

    def consume(self, tokens=1):
        while True:
            with self.lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
            time.sleep(0.1)

RATE_LIMIT_CONFIG = {
    "bucket_capacity": 10000,
    "refill_rate": 5000,
}
token_bucket = TokenBucket(RATE_LIMIT_CONFIG["bucket_capacity"], RATE_LIMIT_CONFIG["refill_rate"])

MAX_CHUNK_CHARS = 3000

def store_analysis(engine, schedule_id: str, analysis_text: str):
    with engine.begin() as conn:
        conn.execute(
            analysis_history_table.insert(),
            {
                "schedule_id": schedule_id,
                "analysis_text": analysis_text,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

def format_tasks_table(tasks: list) -> str:
    if not tasks:
        return "No tasks found."
    table_md = "task_id | task_name | percent_done | bl_start | bl_finish\n"
    table_md += "--- | --- | --- | --- | ---\n"
    for t in tasks:
        table_md += f"{t['task_id']} | {t['task_name']} | {t.get('percent_done', 0)} | {t.get('bl_start','')} | {t.get('bl_finish','')}\n"
    return table_md

def compare_schedules_tool(schedule_id: str) -> str:
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)
    if "error" in result:
        return f"ERROR: {result['error']}"
    insights = result.get("insights", [])
    if not insights:
        return f"No major deviations for schedule {schedule_id}"
    return "\n".join(insights)

def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    if len(text) <= max_chars:
        return [text]
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    for line in lines:
        if current_length + len(line) + 1 > max_chars:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks

def summarize_chunk(chunk: str) -> str:
    token_bucket.consume()
    llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    system_msg = SystemMessage(content="you are a helpful schedule analysis assistant. Please summarize the following context concisely.")
    user_msg = HumanMessage(content=f"Context:\n\n{chunk}\n\nProvide a concise summary.")
    response = llm([system_msg, user_msg])
    return response.content

def summarize_large_context(context: str) -> str:
    chunks = chunk_text(context, MAX_CHUNK_CHARS)
    summaries = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"[Progress] Summarizing chunk {i}/{len(chunks)}")
        summaries.append(summarize_chunk(chunk))
    combined = "\n".join(summaries)
    token_bucket.consume()
    llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    system_msg = SystemMessage(content="you are a helpful schedule analysis assistant.")
    user_msg = HumanMessage(content=f"Here are summaries:\n\n{combined}\n\nCombine them into one final summary.")
    response = llm([system_msg, user_msg])
    return response.content

def summarize_behind_tasks(raw_analysis: str) -> str:
    if len(raw_analysis) > MAX_CHUNK_CHARS:
        return summarize_large_context(raw_analysis)
    else:
        token_bucket.consume()
        llm = ChatOpenAI(model_name="gpt-4", temperature=0)
        system_msg = SystemMessage(content="you are a helpful schedule analysis assistant. Extract and summarize tasks behind schedule concisely.")
        user_msg = HumanMessage(content=f"Context:\n\n{raw_analysis}\n\nSummarize behind-schedule tasks concisely.")
        response = llm([system_msg, user_msg])
        return response.content

def generate_plan(user_query: str) -> list:
    token_bucket.consume()
    llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    system_msg = SystemMessage(content=(
        "you are a planning assistant for construction schedule analysis. "
        "Given a user query, output a JSON array of steps with keys 'action' and 'description'."
    ))
    user_msg = HumanMessage(content=f"Generate a plan in JSON for the following query: {user_query}")
    response = llm([system_msg, user_msg])
    try:
        plan = json.loads(response.content)
        return plan
    except Exception:
        return [{"action": "finalize", "description": "Could not generate plan, use default analysis."}]

def execute_plan(schedule_id: str, plan: list) -> str:
    engine = init_db()
    agent = ConstructionAgent(engine)
    results = []
    for idx, step in enumerate(plan, start=1):
        action = step.get("action")
        print(f"[Progress] Executing step {idx}/{len(plan)}: {action}")
        if action == "fetch_table":
            tasks = agent.fetch_tasks(schedule_id, "target")
            results.append("fetch_table result:\n" + format_tasks_table(tasks))
        elif action == "analyze_progress":
            analysis = compare_schedules_tool(schedule_id)
            results.append("analyze_progress result:\n" + analysis)
        elif action == "summarize":
            context = "\n".join(results)
            summary = summarize_behind_tasks(context)
            results.append("summarize result:\n" + summary)
        elif action == "finalize":
            context = "\n".join(results)
            token_bucket.consume()
            llm = ChatOpenAI(model_name="gpt-4", temperature=0)
            system_msg = SystemMessage(content="you are a helpful construction schedule assistant.")
            user_msg = HumanMessage(content=f"Using the following context:\n\n{context}\n\n{step.get('description','')}\n\nProvide a final answer.")
            response = llm([system_msg, user_msg])
            results.append("finalize result:\n" + response.content)
        else:
            results.append(f"Unrecognized action: {action}")
    return results[-1] if results else "No steps executed."

def run_llm_agent(schedule_id: str, user_query: str) -> str:
    engine = init_db()
    metadata.create_all(engine)
    print("[Progress] Generating plan...")
    plan = generate_plan(user_query)
    print("[Progress] Executing plan...")
    final_text = execute_plan(schedule_id, plan)
    store_analysis(engine, schedule_id, final_text)
    print("[Progress] Analysis stored and complete.")
    return final_text