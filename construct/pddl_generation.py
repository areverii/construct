# construct/pddl_generation.py
import os
from datetime import datetime
from sqlalchemy import select, delete, insert
from construct.database import projects_table, tasks_table, pddl_mappings_table

def compute_duration(bl_start: str, bl_finish: str) -> float:
    """Compute task duration in days given baseline start and finish strings (ISO format)."""
    try:
        start_dt = datetime.fromisoformat(bl_start)
        finish_dt = datetime.fromisoformat(bl_finish)
        duration = (finish_dt - start_dt).total_seconds() / (3600 * 24)
        return duration if duration > 0 else 0.1
    except Exception:
        return 1

def assign_chunks(tasks: list, chunk_length_days: int = 28) -> list:
    """
    Assign each task a chunk (e.g., "chunk_0", "chunk_1", …)
    based on its baseline start time.
    Returns a sorted list of unique chunk names.
    """
    valid_tasks = [t for t in tasks if t.get("bl_start")]
    project_start = min((datetime.fromisoformat(t["bl_start"]) for t in valid_tasks), default=datetime.utcnow())
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
    """
    Query the database for tasks with the given schedule_id and schedule_type 'target'
    (i.e. the target schedule), then generate the PDDL domain and problem strings.
    """
    with engine.connect() as conn:
        task_rows = conn.execute(
            select(tasks_table).where(tasks_table.c.schedule_id == schedule_id)
                                 .where(tasks_table.c.schedule_type == "target")
        ).fetchall()
    tasks = [dict(r._mapping) for r in task_rows]

    for t in tasks:
        if (not t.get("duration") or t.get("duration") <= 0) and t.get("bl_start") and t.get("bl_finish"):
            t["duration"] = compute_duration(t["bl_start"], t["bl_finish"])
        elif not t.get("duration"):
            t["duration"] = 1

    chunks = assign_chunks(tasks, chunk_length_days)

    domain_lines = [
        "(define (domain construction)",
        "  (:requirements :typing :durative-actions :fluents)",
        "  (:types task chunk)",
        "  (:predicates",
        "     (done ?t - task)",
        "     (in-chunk ?t - task ?c - chunk)",
        "     (chunk-order ?c1 - chunk ?c2 - chunk)",
        "  )"
    ]
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

    problem_lines = [
        f"(define (problem proj_{schedule_id})",
        "  (:domain construction)",
        "  (:objects"
    ]
    for t in tasks:
        problem_lines.append(f"     t_{t['task_id']} - task")
    for c in chunks:
        problem_lines.append(f"     {c} - chunk")
    problem_lines.append("  )")
    problem_lines.append("  (:init")
    for t in tasks:
        problem_lines.append(f"     (in-chunk t_{t['task_id']} {t['chunk']})")
    for i in range(len(chunks) - 1):
        problem_lines.append(f"     (chunk-order {chunks[i]} {chunks[i+1]})")
    problem_lines.append("  )")
    problem_lines.append("  (:goal (and")
    for t in tasks:
        problem_lines.append(f"     (done t_{t['task_id']})")
    problem_lines.append("  ))")
    problem_lines.append(")")
    problem_str = "\n".join(problem_lines)

    return domain_str, problem_str

def generate_pddl_for_schedule(schedule_id: str, engine):
    # Determine the project folder from the engine’s SQLite database file location.
    project_folder = os.path.dirname(os.path.abspath(engine.url.database))
    os.makedirs(project_folder, exist_ok=True)
    
    domain_str, problem_str = generate_domain_and_problem(schedule_id, engine)
    base_name = f"{schedule_id}_{int(datetime.utcnow().timestamp())}_opt"
    domain_path = os.path.join(project_folder, f"{base_name}_domain.pddl")
    problem_path = os.path.join(project_folder, f"{base_name}_problem.pddl")
    with open(domain_path, "w") as f:
        f.write(domain_str)
    with open(problem_path, "w") as f:
        f.write(problem_str)
    
    from sqlalchemy import delete, insert
    with engine.begin() as conn:
        conn.execute(
            delete(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == schedule_id)
        )
        conn.execute(
            insert(pddl_mappings_table),
            {
                "schedule_id": schedule_id,
                "domain_file": domain_path,
                "problem_file": problem_path,
                "created_at": datetime.utcnow().isoformat()
            }
        )