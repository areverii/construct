import os
import datetime
from sqlalchemy import select, delete, insert
from collections import defaultdict
from construct.database import (
    projects_table, tasks_table, dependencies_table,
    pddl_mappings_table
)

gen_folder = "gen"
os.makedirs(gen_folder, exist_ok=True)

def save_pddl(domain_str: str, problem_str: str, base_name: str):
    domain_path = os.path.join(gen_folder, f"{base_name}_domain.pddl")
    problem_path = os.path.join(gen_folder, f"{base_name}_problem.pddl")
    with open(domain_path, "w") as f:
        f.write(domain_str)
    with open(problem_path, "w") as f:
        f.write(problem_str)
    return domain_path, problem_path

def _parse_dt(s):
    """Helper to parse a 'YYYY-MM-DD HH:MM:SS' string into a datetime, or None."""
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def _compute_duration_if_missing(task):
    """If no positive duration, compute from (bl_finish - bl_start), in days."""
    dur = task.get("duration")
    if dur and dur > 0:
        return dur
    start_str = task.get("bl_start")
    fin_str = task.get("bl_finish")
    start_dt = _parse_dt(start_str)
    fin_dt = _parse_dt(fin_str)
    if start_dt and fin_dt and fin_dt > start_dt:
        delta = fin_dt - start_dt
        return delta.total_seconds() / 86400.0
    return None

def _build_parent_map(tasks):
    """Return a dict: parent_id -> list of child task_ids."""
    pmap = defaultdict(list)
    for t in tasks:
        p = t.get("parent_id")
        if p:
            pmap[p].append(t["task_id"])
    return pmap

def schedule_to_pddl(schedule_id: str, engine):
    """Collect tasks, skip summary rows, ensure valid durations, then build domain/problem."""
    # fetch project row
    with engine.connect() as conn:
        proj = conn.execute(
            select(projects_table)
            .where(projects_table.c.schedule_id == schedule_id)
            .where(projects_table.c.schedule_type == "target")
        ).fetchone()
        if not proj:
            raise ValueError(f"no target project found for {schedule_id}")

        # gather tasks
        rows = conn.execute(
            select(tasks_table)
            .where(tasks_table.c.schedule_id == schedule_id)
            .where(tasks_table.c.schedule_type == "target")
        ).fetchall()
        all_tasks = [dict(r._mapping) for r in rows]

        # gather dependencies
        deps = conn.execute(
            select(dependencies_table)
            .where(dependencies_table.c.schedule_id == schedule_id)
        ).fetchall()
        deps = [dict(d._mapping) for d in deps]

    if not all_tasks:
        raise ValueError(f"no tasks found for {schedule_id}")

    # build parent->children map
    pmap = _build_parent_map(all_tasks)

    # separate leaf tasks vs. summaries
    leaf_tasks = []
    for t in all_tasks:
        tid = t["task_id"]
        # if this tid has children, it's a summary -> skip
        if tid in pmap and len(pmap[tid]) > 0:
            # summary row
            continue
        # compute or confirm duration
        final_dur = _compute_duration_if_missing(t)
        t["final_duration"] = final_dur
        # if final_dur <= 0 => skip or treat as milestone
        if not final_dur or final_dur <= 0:
            print(f"Skipping 0-duration task or invalid baseline: {t['task_name']} ({tid})")
            continue
        leaf_tasks.append(t)

    if not leaf_tasks:
        raise ValueError(f"no valid leaf tasks found for {schedule_id}")

    # build domain
    domain_str = "(define (domain construction)\n"
    domain_str += "  (:requirements :typing :durative-actions)\n"
    domain_str += "  (:types task)\n\n"
    for t in leaf_tasks:
        tid = t["task_id"]
        domain_str += f"  (:durative-action do_{tid}\n"
        domain_str += f"     :parameters ()\n"
        domain_str += f"     :duration (= ?duration {t['final_duration']})\n"
        domain_str += "     :condition (and (at start (not-done)))\n"
        domain_str += "     :effect (and (at end (done)))\n"
        domain_str += "  )\n"
    domain_str += ")\n"

    # build problem
    problem_str = f"(define (problem proj_{schedule_id})\n"
    problem_str += "  (:domain construction)\n"
    # objects
    problem_str += "  (:objects\n"
    for t in leaf_tasks:
        problem_str += f"    t_{t['task_id']} - task\n"
    problem_str += "  )\n\n"
    # init
    problem_str += "  (:init\n"
    # optional, insert constraints from dependencies
    for d in deps:
        problem_str += f"    ;; must finish {d['depends_on_task_id']} before {d['task_id']}\n"
    problem_str += "    (not-done)\n"
    problem_str += "  )\n"
    # trivial goal
    problem_str += "  (:goal (and (done)))\n"
    problem_str += ")\n"

    return domain_str, problem_str

def generate_pddl_for_schedule(schedule_id: str, engine):
    """Main entry point for PDDL generation from a target schedule."""
    domain_str, problem_str = schedule_to_pddl(schedule_id, engine)
    # pick a filename
    base_name = f"{schedule_id}_{int(datetime.datetime.utcnow().timestamp())}"
    domain_path, problem_path = save_pddl(domain_str, problem_str, base_name)

    # store or update mapping
    with engine.begin() as conn:
        conn.execute(
            delete(pddl_mappings_table)
            .where(pddl_mappings_table.c.schedule_id == schedule_id)
        )
        conn.execute(
            insert(pddl_mappings_table),
            {
                "schedule_id": schedule_id,
                "domain_file": domain_path,
                "problem_file": problem_path,
                "created_at": str(datetime.datetime.utcnow())
            }
        )

def get_latest_pddl_mapping(schedule_id: str, engine):
    with engine.connect() as conn:
        row = conn.execute(
            select(pddl_mappings_table)
            .where(pddl_mappings_table.c.schedule_id == schedule_id)
            .order_by(pddl_mappings_table.c.id.desc())
        ).fetchone()
    if not row:
        return None
    return dict(row._mapping)