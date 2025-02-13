import os
from datetime import datetime, timezone
from sqlalchemy import select, insert, update
from construct.database import tasks_table, pddl_mappings_table
from construct.utils import compute_duration
from construct.assign_chunks import assign_chunks

# Generate the domain PDDL for a target schedule in an idempotent fashion.
def generate_domain_for_target(schedule_id: str, engine, output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join("gen", f"schedule_{schedule_id}")
    os.makedirs(output_dir, exist_ok=True)
    domain_file = os.path.join(output_dir, "domain.pddl")
    
    # Check for an existing mapping for the target schedule (chunk is None)
    with engine.connect() as conn:
        query = select(pddl_mappings_table).where(
            (pddl_mappings_table.c.schedule_id == schedule_id) &
            (pddl_mappings_table.c.chunk.is_(None))
        )
        mapping = conn.execute(query).mappings().first()
    
    # If a mapping exists and the domain file is present, just return it.
    if mapping and os.path.isfile(mapping["domain_file"]):
        return mapping["domain_file"]
    
    # Otherwise, generate the domain content
    domain_str = generate_domain(schedule_id, engine)
    with open(domain_file, "w") as f:
        f.write(domain_str)
    
    # Upsert the mapping entry
    with engine.begin() as conn:
        if mapping:
            conn.execute(
                update(pddl_mappings_table)
                .where((pddl_mappings_table.c.schedule_id == schedule_id) &
                       (pddl_mappings_table.c.chunk.is_(None)))
                .values(domain_file=domain_file, created_at=datetime.now(timezone.utc).isoformat())
            )
        else:
            conn.execute(insert(pddl_mappings_table), {
                "schedule_id": schedule_id,
                "chunk": None,  # Indicates this mapping is for the domain PDDL
                "domain_file": domain_file,
                "problem_file": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    return domain_file


def generate_domain(schedule_id: str, engine) -> str:
    """
    Generate a domain definition for the entire schedule.
    Assumes all tasks for the schedule are needed.
    """
    with engine.connect() as conn:
        task_rows = conn.execute(
            select(tasks_table).where(tasks_table.c.schedule_id == schedule_id)
        ).fetchall()
    tasks = [dict(r._mapping) for r in task_rows]
    
    # Make sure durations are computed
    for t in tasks:
        if (not t.get("duration")) and t.get("bl_start") and t.get("bl_finish"):
            t["duration"] = compute_duration(t["bl_start"], t["bl_finish"])
        elif not t.get("duration"):
            t["duration"] = 1

    # Use all tasks to produce the actions; we assume every task gets an action.
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
        chunk = t.get("chunk", "chunk_0")  # default in case not set
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
    return domain_str

def generate_problem_for_chunk(schedule_id: str, engine, tasks: list, chunks: list, current_chunk: str) -> str:
    """
    Generate a problem definition for a given chunk.
    For tasks in chunks prior to the current chunk, assume they are done.
    For tasks in the current chunk, mark them as in-chunk.
    Tasks in later chunks are omitted.
    The goal is to have all tasks in the current chunk done.
    """
    # Determine current chunk index from the name (e.g., "chunk_0" → 0)
    current_index = int(current_chunk.split("_")[1])
    
    # Filter tasks into three groups
    tasks_done = [t for t in tasks if int(t["chunk"].split("_")[1]) < current_index]
    tasks_current = [t for t in tasks if t["chunk"] == current_chunk]
    
    # Objects: include tasks that are done or in this chunk
    tasks_in_problem = tasks_done + tasks_current
    
    problem_lines = []
    problem_lines.append(f"(define (problem proj_{schedule_id}_{current_chunk})")
    problem_lines.append("  (:domain construction)")
    problem_lines.append("  (:objects")
    for t in tasks_in_problem:
        problem_lines.append(f"     t_{t['task_id']} - task")
    # Include chunk objects: only include chunks up to and including the current chunk
    for c in chunks:
        if int(c.split("_")[1]) <= current_index:
            problem_lines.append(f"     {c} - chunk")
    problem_lines.append("  )")
    
    # Initial state: for tasks in earlier chunks, mark as done;
    # for tasks in the current chunk, add their in-chunk predicate.
    problem_lines.append("  (:init")
    for t in tasks_done:
        problem_lines.append(f"     (done t_{t['task_id']})")
    for t in tasks_current:
        problem_lines.append(f"     (in-chunk t_{t['task_id']} {t['chunk']})")
    # Optionally, if you need chunk order among included chunks, add that here.
    # For all included chunks (sorted), add ordering predicates.
    included_chunks = [c for c in chunks if int(c.split("_")[1]) <= current_index]
    for i in range(len(included_chunks) - 1):
        problem_lines.append(f"     (chunk-order {included_chunks[i]} {included_chunks[i+1]})")
    problem_lines.append("  )")
    
    # The goal: all tasks in the current chunk are done.
    problem_lines.append("  (:goal (and")
    for t in tasks_current:
        problem_lines.append(f"     (done t_{t['task_id']})")
    problem_lines.append("  ))")
    problem_lines.append(")")
    problem_str = "\n".join(problem_lines)
    return problem_str

# Generates PDDL files (both domain and problem) for an in-progress schedule in an idempotent fashion.
def generate_pddl_chunks_for_schedule(schedule_id: str, engine, chunk_length_days: int = 28, output_dir: str = None):
    if output_dir is None:
        output_dir = os.path.join("gen", f"schedule_{schedule_id}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Retrieve tasks for this schedule.
    with engine.connect() as conn:
        task_rows = conn.execute(
            select(tasks_table).where(tasks_table.c.schedule_id == schedule_id)
        ).fetchall()
    tasks = [dict(r._mapping) for r in task_rows]
    
    # Compute missing durations using the shared helper.
    for t in tasks:
        if not t.get("duration"):
            if t.get("bl_start") and t.get("bl_finish"):
                t["duration"] = compute_duration(t["bl_start"], t["bl_finish"])
            else:
                t["duration"] = 1
    
    # Assign chunks to tasks.
    chunks = assign_chunks(tasks, chunk_length_days)
    
    # Choose the "current" chunk (for example, the last in the sorted order).
    current_chunk = sorted(chunks, key=lambda x: int(x.split("_")[1]))[-1]
    
    # Check for an existing mapping for this in-progress schedule.
    with engine.connect() as conn:
        query = select(pddl_mappings_table).where(
            (pddl_mappings_table.c.schedule_id == schedule_id) &
            (pddl_mappings_table.c.chunk.is_(None))
        )
        mapping = conn.execute(query).mappings().first()
    
    # Generate the domain; if the domain file doesn't exist, write it.
    domain_str = generate_domain(schedule_id, engine)
    domain_file = os.path.join(output_dir, "domain.pddl")
    if not (mapping and os.path.isfile(domain_file)):
        with open(domain_file, "w") as f:
            f.write(domain_str)
    
    # Generate the problem file for the current chunk.
    # (Assumes generate_problem_for_chunk is defined to return the problem PDDL as a string.)
    problem_str = generate_problem_for_chunk(schedule_id, engine, tasks, chunks, current_chunk)
    problem_file = os.path.join(output_dir, f"problem_{current_chunk}.pddl")
    if not os.path.isfile(problem_file):
        with open(problem_file, "w") as f:
            f.write(problem_str)
    
    # Upsert the mapping entry to include both the domain and problem file paths.
    with engine.begin() as conn:
        if mapping:
            conn.execute(
                update(pddl_mappings_table)
                .where((pddl_mappings_table.c.schedule_id == schedule_id) &
                       (pddl_mappings_table.c.chunk.is_(None)))
                .values(domain_file=domain_file, problem_file=problem_file,
                        created_at=datetime.now(timezone.utc).isoformat())
            )
        else:
            conn.execute(insert(pddl_mappings_table), {
                "schedule_id": schedule_id,
                "chunk": None,
                "domain_file": domain_file,
                "problem_file": problem_file,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {"domain": domain_file, "problems": {current_chunk: problem_file}}