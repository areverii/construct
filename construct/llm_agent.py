# construct/llm_agent.py

import json
from datetime import datetime

from sqlalchemy import Table, Column, Integer, String, MetaData
from construct.database import init_db
from construct.agent import ConstructionAgent

# We'll do direct LLM calls for summarization
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

metadata = MetaData()

analysis_table = Table(
    "analysis_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("schedule_id", String),
    Column("analysis_text", String),
    Column("timestamp", String),
)

def store_analysis(engine, schedule_id: str, analysis_text: str):
    with engine.begin() as conn:
        conn.execute(
            analysis_table.insert(),
            {
                "schedule_id": schedule_id,
                "analysis_text": analysis_text,
                "timestamp": str(datetime.utcnow())
            }
        )

def compare_schedules_tool(schedule_id: str) -> str:
    """
    Returns the raw text from analyzing the target vs. in-progress schedule.
    (Behind / Ahead lines, one per task.)
    """
    engine = init_db()
    agent = ConstructionAgent(engine)
    result = agent.analyze_progress(schedule_id)

    if "error" in result:
        return f"ERROR: {result['error']}"

    insights = result.get("insights", [])
    if not insights:
        return f"No major deviations for schedule {schedule_id}"

    return "\n".join(insights)

def summarize_behind_tasks(raw_analysis: str) -> str:
    """
    Calls GPT to read the raw analysis text and produce a short behind-schedule summary.
    """
    # We'll assume you have an OPENAI_API_KEY loaded.
    # If you have GPT-4 access, use model_name="gpt-4"; otherwise "gpt-3.5-turbo."
    llm = ChatOpenAI(model_name="gpt-4", temperature=0)

    # We craft a prompt with system + user messages
    system_msg = SystemMessage(content=(
        "You are a helpful schedule analysis assistant. "
        "The user has a list of tasks behind or ahead of schedule."
        "Please extract only the behind-schedule tasks, grouped or summarized succinctly."
    ))
    user_msg = HumanMessage(content=(
        f"Here is the raw tool output:\n\n{raw_analysis}\n\n"
        "Please summarize only the tasks that are behind schedule, in a concise way."
    ))

    response = llm([system_msg, user_msg])
    return response.content

def run_llm_agent(schedule_id: str, user_query: str) -> str:
    """
    1) Get the raw analysis from compare_schedules_tool
    2) Summarize it focusing on behind-schedule tasks (or whatever user_query suggests)
    3) Store and return the final text
    """
    engine = init_db()
    metadata.create_all(engine)

    # Step 1: get raw lines of behind/ahead tasks
    raw_analysis = compare_schedules_tool(schedule_id)

    # Step 2: use the user_query to decide how we want to summarize
    # For now, we just always call summarize_behind_tasks, but you could parse user_query differently
    if "behind-schedule" in user_query.lower():
        final_text = summarize_behind_tasks(raw_analysis)
    else:
        # or you might have a different summarizer or just return raw
        final_text = raw_analysis

    store_analysis(engine, schedule_id, final_text)
    return final_text