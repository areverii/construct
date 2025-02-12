# construct/pddl_generation.py
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete, insert
from construct.database import projects_table, tasks_table, pddl_mappings_table

GEN_FOLDER = "gen"
os.makedirs(GEN_FOLDER, exist_ok=True)

def compute_duration(bl_start: str, bl_finish: str) -> float:
    """Compute task duration in days given baseline start and finish strings in ISO format."""
    try:
        start_dt = datetime.fromisoformat(bl_start)
        finish_dt = datetime.fromisoformat(bl_finish)
        duration = (finish_dt - start_dt).total_seconds() / (3600 * 24)
        return duration if duration > 0 else 0.1
    except Exception as e:
        return 1

def assign_chunks(tasks: list, chunk_length_days: int = 28) -> list:
    """
    Assign each task a chunk based on its baseline start time.
    Returns a sorted list of unique chunk names and updates each task with a 'chunk' key.
    """
    valid_tasks = [t for t in tasks if t.get("bl_start")]
    if valid_tasks:
        project_start = min(datetime.fromisoformat(t["bl_start"]) for t in valid_tasks)
    else:
        project_start = datetime.now(timezone.utc)
    
    for t in tasks:
        if t.get("bl_start"):
            start_dt = datetime.fromisoformat(t["bl_start"])
            chunk_index = int((start_dt - project_start).days // chunk_length_days)
        else:
            chunk_index = 0
        t["chunk"] = f"chunk_{chunk_index}"
    
    chunk_set = {t["chunk"] for t in tasks}
    sorted_chunks = sorted(chunk_set, key=lambda c: int(c.split("_")[1]))
    return sorted_chunks

def generate_domain_and_problem(schedule_id: str, engine, chunk_length_days: int = 28):
    # Retrieve all tasks (both target and in-progress) for the given schedule.
    with engine.connect() as conn:
        task_rows = conn.execute(
            select(tasks_table).where(tasks_table.c.schedule_id == schedule_id)
        ).fetchall()
    tasks = [dict(r._mapping) for r in task_rows]

    # Compute duration where missing.
    for t in tasks:
        if (not t.get("duration")) and t.get("bl_start") and t.get("bl_finish"):
            t["duration"] = compute_duration(t["bl_start"], t["bl_finish"])
        elif not t.get("duration"):
            t["duration"] = 1

    # Assign chunks.
    chunks = assign_chunks(tasks, chunk_length_days)

    # Build the domain definition.
    domain_lines = []
    domain_lines.append("(define (domain construction)")
    domain_lines.append("  (:requirements :typing :durative-actions :fluents)")
    domain_lines.append("  (:types task chunk)")
    domain_lines.append("  (:predicates")
    domain_lines.append("     (done ?t - task)")
    domain_lines.append("     (in-chunk ?t - task ?c - chunk)")
    domain_lines.append("     (chunk-order ?c1 - chunk ?c2 - chunk)")
    domain_lines.append("  )")
    
    for t in tasks:
        action_name = f"do_{t['task_id']}"
        duration = t["duration"]
        chunk = t["chunk"]
        action = (
            f"  (:durative-action {action_name}\n"
            "     :parameters ()\n"
            f"     :duration (= ?duration {duration})\n"
            "     :condition (and\n"
            f"                   (in-chunk t_{t['task_id']} {chunk})\n"
            f"                   (at start (not (done t_{t['task_id']})))\n"
            "                 )\n"
            f"     :effect (at end (done t_{t['task_id']}))\n"
            "  )"
        )
        domain_lines.append(action)
    domain_lines.append(")")
    domain_str = "\n".join(domain_lines)

    # Build the problem definition.
    problem_lines = []
    problem_lines.append(f"(define (problem proj_{schedule_id})")
    problem_lines.append("  (:domain construction)")
    problem_lines.append("  (:objects")
    for t in tasks:
        problem_lines.append(f"     t_{t['task_id']} - task")
    for c in chunks:
        problem_lines.append(f"     {c} - chunk")
    problem_lines.append("  )")
    
    # In the initial state, mark tasks as done if percent_done >= 100, else assign them to their chunk.
    problem_lines.append("  (:init")
    for t in tasks:
        try:
            percent = float(t.get("percent_done") or 0.0)
        except ValueError:
            percent = 0.0
        if percent >= 100.0:
            problem_lines.append(f"     (done t_{t['task_id']})")
        else:
            problem_lines.append(f"     (in-chunk t_{t['task_id']} {t['chunk']})")
    # Add chunk ordering.
    for i in range(len(chunks) - 1):
        problem_lines.append(f"     (chunk-order {chunks[i]} {chunks[i+1]})")
    problem_lines.append("  )")
    
    # The goal is that every task is done.
    problem_lines.append("  (:goal (and")
    for t in tasks:
        problem_lines.append(f"     (done t_{t['task_id']})")
    problem_lines.append("  ))")
    problem_lines.append(")")
    problem_str = "\n".join(problem_lines)
    
    return domain_str, problem_str

def save_pddl(domain_str: str, problem_str: str, base_name: str):
    domain_path = os.path.join(GEN_FOLDER, f"{base_name}_domain.pddl")
    problem_path = os.path.join(GEN_FOLDER, f"{base_name}_problem.pddl")
    with open(domain_path, "w") as f:
        f.write(domain_str)
    with open(problem_path, "w") as f:
        f.write(problem_str)
    return domain_path, problem_path

def generate_pddl_for_schedule(schedule_id: str, engine, output_dir: str = None):
    """
    Generate PDDL files for a given schedule_id. If output_dir is provided,
    the files will be written there. Otherwise, a default folder under 'gen' will be used.
    """
    if output_dir is None:
        output_dir = os.path.join("gen", f"schedule_{schedule_id}")
    os.makedirs(output_dir, exist_ok=True)
    
    domain_file = os.path.join(output_dir, "domain.pddl")
    problem_file = os.path.join(output_dir, "problem.pddl")
    
    domain_content = f"; Domain file for schedule {schedule_id}\n; Generated on {datetime.now(timezone.utc).isoformat()}\n"
    problem_content = f"; Problem file for schedule {schedule_id}\n; Generated on {datetime.now(timezone.utc).isoformat()}\n"
    
    with open(domain_file, "w") as f:
        f.write(domain_content)
    with open(problem_file, "w") as f:
        f.write(problem_content)
    
    with engine.begin() as conn:
        conn.execute(insert(pddl_mappings_table), {
            "schedule_id": schedule_id,
            "domain_file": domain_file,
            "problem_file": problem_file,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"domain": domain_file, "problem": problem_file}