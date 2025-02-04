# construct/pddl_generation.py
import os
from datetime import datetime, timedelta
from sqlalchemy import select, delete, insert
from construct.database import projects_table, tasks_table, dependencies_table, pddl_mappings_table

GEN_FOLDER = "gen"
os.makedirs(GEN_FOLDER, exist_ok=True)

def save_pddl(domain_str: str, problem_str: str, base_name: str):
    domain_path = os.path.join(GEN_FOLDER, f"{base_name}_domain.pddl")
    problem_path = os.path.join(GEN_FOLDER, f"{base_name}_problem.pddl")
    with open(domain_path, "w") as f:
        f.write(domain_str)
    with open(problem_path, "w") as f:
        f.write(problem_str)
    return domain_path, problem_path

def generate_optimized_pddl(schedule_id: str, engine, chunk_duration_days: int = 28):
    """
    Generate a PDDL domain and problem that:
      - Groups tasks into time chunks (e.g. 28‑day intervals)
      - Introduces a new type “chunk” and predicates for task grouping and ordering.
    This is intended to be a starting point for a scheduling formulation that can
    later be fed into a planner (e.g. OPTIC) to generate candidate schedules.
    """
    # Query target schedule tasks
    with engine.connect() as conn:
        result = conn.execute(
            select(tasks_table).where(
                tasks_table.c.schedule_id == schedule_id,
                tasks_table.c.schedule_type == "target"
            )
        )
        tasks = [dict(row._mapping) for row in result]
    if not tasks:
        raise ValueError(f"No target tasks found for schedule_id {schedule_id}")

    # Convert baseline start/finish strings to datetime objects.
    for t in tasks:
        if t.get("bl_start"):
            t["bl_start_dt"] = datetime.strptime(t["bl_start"], "%Y-%m-%d %H:%M:%S")
        else:
            t["bl_start_dt"] = None
        if t.get("bl_finish"):
            t["bl_finish_dt"] = datetime.strptime(t["bl_finish"], "%Y-%m-%d %H:%M:%S")
        else:
            t["bl_finish_dt"] = None

    # Determine overall project baseline start and finish
    valid_starts = [t["bl_start_dt"] for t in tasks if t["bl_start_dt"] is not None]
    valid_finishes = [t["bl_finish_dt"] for t in tasks if t["bl_finish_dt"] is not None]
    if not valid_starts or not valid_finishes:
        raise ValueError("Cannot compute project boundaries from tasks.")
    project_start = min(valid_starts)
    project_finish = max(valid_finishes)

    # Determine the number of chunks needed
    total_days = (project_finish - project_start).days
    num_chunks = (total_days // chunk_duration_days) + 1

    # Assign each task a chunk based on its baseline start time
    for t in tasks:
        if t["bl_start_dt"]:
            t["chunk"] = int((t["bl_start_dt"] - project_start).days // chunk_duration_days)
        else:
            t["chunk"] = 0

    # ----- Build Domain PDDL -----
    domain_lines = []
    domain_lines.append("(define (domain construction)")
    domain_lines.append("  (:requirements :typing :durative-actions :fluents)")
    domain_lines.append("  (:types task chunk)")
    domain_lines.append("  (:predicates")
    domain_lines.append("     (done ?t - task)")
    domain_lines.append("     (in-chunk ?t - task ?c - chunk)")
    domain_lines.append("     (chunk-order ?c1 - chunk ?c2 - chunk)")  # c1 comes before c2
    domain_lines.append("  )")
    # For each task, create a durative action.
    # (This simple formulation simply “executes” the task within its designated chunk.)
    for t in tasks:
        tid = t["task_id"]
        duration = t["duration"] if t.get("duration") is not None else 1
        chunk = t["chunk"]
        domain_lines.append(f"  (:durative-action do_{tid}")
        domain_lines.append("     :parameters ()")
        domain_lines.append(f"     :duration (= ?duration {duration})")
        domain_lines.append("     :condition (and")
        domain_lines.append(f"                   (in-chunk t_{tid} chunk_{chunk})")
        domain_lines.append(f"                   (at start (not (done t_{tid})))")
        domain_lines.append("                 )")
        domain_lines.append("     :effect (at end (done t_{tid}))")
        domain_lines.append("  )")
    domain_lines.append(")")
    domain_str = "\n".join(domain_lines)

    # ----- Build Problem PDDL -----
    problem_lines = []
    problem_lines.append(f"(define (problem proj_{schedule_id})")
    problem_lines.append("  (:domain construction)")
    # Declare objects: tasks and chunks
    task_objs = " ".join(f"t_{t['task_id']}" for t in tasks)
    chunk_objs = " ".join(f"chunk_{i}" for i in range(num_chunks))
    problem_lines.append("  (:objects")
    problem_lines.append(f"     {task_objs} - task")
    problem_lines.append(f"     {chunk_objs} - chunk")
    problem_lines.append("  )")
    # Init: assign each task its chunk and define the ordering between chunks
    problem_lines.append("  (:init")
    for t in tasks:
        problem_lines.append(f"     (in-chunk t_{t['task_id']} chunk_{t['chunk']})")
    for i in range(num_chunks - 1):
        problem_lines.append(f"     (chunk-order chunk_{i} chunk_{i+1})")
    problem_lines.append("  )")
    # Goal: every task must be done.
    problem_lines.append("  (:goal (and")
    for t in tasks:
        problem_lines.append(f"     (done t_{t['task_id']})")
    problem_lines.append("  ))")
    # (Optionally, add a metric for optimization here if your planner supports it.)
    problem_lines.append(")")
    problem_str = "\n".join(problem_lines)

    # Save the generated domain and problem files.
    base_name = f"{schedule_id}_{int(datetime.utcnow().timestamp())}_opt"
    domain_path, problem_path = save_pddl(domain_str, problem_str, base_name)

    # Update the pddl mapping table in the database.
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
                "created_at": str(datetime.utcnow())
            }
        )
    return domain_str, problem_str

def generate_simple_pddl(schedule_id: str, engine):
    """
    The original (simple) PDDL generation implementation.
    """
    with engine.connect() as conn:
        project = conn.execute(
            select(projects_table)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == "target")
        ).fetchone()
        if not project:
            raise ValueError(f"no target project found for {schedule_id}")
        tasks_result = conn.execute(
            select(tasks_table)
            .where(tasks_table.c.schedule_id == schedule_id)
            .where(tasks_table.c.schedule_type == "target")
        ).fetchall()
        tasks = [dict(r._mapping) for r in tasks_result]
        dependencies_result = conn.execute(
            select(dependencies_table)
            .where(dependencies_table.c.schedule_id == schedule_id)
        ).fetchall()
        dependencies = [dict(r._mapping) for r in dependencies_result]
    # Basic validations
    for t in tasks:
        if not t.get("bl_start") or not t.get("bl_finish"):
            raise ValueError(f"missing baseline dates for task {t['task_id']}")
        if not t.get("duration") or t["duration"] <= 0:
            raise ValueError(f"invalid duration for task {t['task_id']}")
    # Build a simple domain as before.
    domain_lines = []
    domain_lines.append("(define (domain construction)")
    domain_lines.append("  (:requirements :typing :durative-actions)")
    domain_lines.append("  (:types task)")
    for t in tasks:
        tid = t["task_id"]
        domain_lines.append(f"  (:durative-action do_{tid}")
        domain_lines.append("     :parameters ()")
        domain_lines.append(f"     :duration (= ?duration {t['duration']})")
        domain_lines.append("     :condition (and (at start (not-done)))")
        domain_lines.append("     :effect (and (at end (done)))")
        domain_lines.append("  )")
    domain_lines.append(")")
    domain_str = "\n".join(domain_lines)
    # Build a simple problem.
    problem_lines = []
    problem_lines.append(f"(define (problem proj_{schedule_id})")
    problem_lines.append("  (:domain construction)")
    problem_lines.append("  (:objects")
    for t in tasks:
        problem_lines.append(f"    t_{t['task_id']} - task")
    problem_lines.append("  )")
    problem_lines.append("  (:init")
    for d in dependencies:
        problem_lines.append(f"    ;; Dependency: task {d['task_id']} depends on {d['depends_on_task_id']}")
    problem_lines.append("    (not-done)")
    problem_lines.append("  )")
    problem_lines.append("  (:goal (and (done)))")
    problem_lines.append(")")
    problem_str = "\n".join(problem_lines)
    base_name = f"{schedule_id}_{int(datetime.utcnow().timestamp())}"
    domain_path, problem_path = save_pddl(domain_str, problem_str, base_name)
    with engine.begin() as conn:
        conn.execute(delete(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == schedule_id))
        conn.execute(insert(pddl_mappings_table),
                     {"schedule_id": schedule_id,
                      "domain_file": domain_path,
                      "problem_file": problem_path,
                      "created_at": str(datetime.utcnow())})
    return domain_str, problem_str

def generate_pddl_for_schedule(schedule_id: str, engine, use_optimized: bool = True, chunk_duration_days: int = 28):
    """
    Depending on the flag, generate either the optimized/chunked PDDL
    or the simple (old) version.
    """
    if use_optimized:
        return generate_optimized_pddl(schedule_id, engine, chunk_duration_days)
    else:
        return generate_simple_pddl(schedule_id, engine)
