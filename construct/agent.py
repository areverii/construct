# construct/agent.py

from construct.database import projects_table, tasks_table, dependencies_table
from sqlalchemy import select
from datetime import datetime

class ConstructionAgent:
    def __init__(self, engine):
        self.engine = engine

    def fetch_tasks(self, schedule_id: str, schedule_type: str):
        with self.engine.connect() as conn:
            result = conn.execute(
                select(tasks_table)
                .where(tasks_table.c.schedule_id == schedule_id)
                .where(tasks_table.c.schedule_type == schedule_type)
            ).fetchall()
            if not result:
                return []
            return [dict(row._mapping) for row in result]

    def compute_expected_percent_done(self, target_task: dict, current_day: datetime) -> float:
        start_str = target_task.get("start_date")
        end_str = target_task.get("end_date")
        if not start_str or not end_str:
            return 0.0

        # parse start/end datetime (handles "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS")
        fmt_start = "%Y-%m-%d %H:%M:%S" if " " in start_str else "%Y-%m-%d"
        fmt_end = "%Y-%m-%d %H:%M:%S" if " " in end_str else "%Y-%m-%d"
        start_dt = datetime.strptime(start_str, fmt_start)
        end_dt = datetime.strptime(end_str, fmt_end)

        if current_day < start_dt:
            return 0.0  # haven't started
        if current_day >= end_dt:
            return 100.0  # should be done by now

        total = (end_dt - start_dt).total_seconds()
        elapsed = (current_day - start_dt).total_seconds()
        fraction = elapsed / total if total > 0 else 0.0
        return min(fraction * 100.0, 100.0)

    def analyze_progress(self, schedule_id: str):
        target_tasks = self.fetch_tasks(schedule_id, "target")
        progress_tasks = self.fetch_tasks(schedule_id, "in-progress")

        if not target_tasks or not progress_tasks:
            return {"error": "Target or in-progress schedule not found"}

        with self.engine.connect() as conn:
            result = conn.execute(
                select(
                    projects_table.c.project_start_date,
                    projects_table.c.project_end_date,
                    projects_table.c.current_in_progress_date
                )
                .where(projects_table.c.schedule_id == schedule_id)
                .where(projects_table.c.schedule_type == "target")
            ).fetchone()

        if not result:
            return {"error": "Project start/end dates not set"}

        def parse_dt(val: str):
            if not val:
                return None
            if " " in val:
                return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(val, "%Y-%m-%d")

        current_day = parse_dt(result[2]) or datetime.utcnow()

        target_dict = {t["task_id"]: t for t in target_tasks}
        progress_dict = {t["task_id"]: t for t in progress_tasks}

        insights = []
        for task_id, target_task in target_dict.items():
            if task_id not in progress_dict:
                continue

            progress = progress_dict[task_id]
            progress_val = progress["percent_done"] or 0.0
            expected_val = self.compute_expected_percent_done(target_task, current_day)

            if progress_val < expected_val:
                insights.append(f"Task '{progress['task_name']}' is behind schedule (progress: {progress_val}%, expected: {expected_val:.1f}%).")
            elif progress_val > expected_val:
                insights.append(f"Task '{progress['task_name']}' is ahead of schedule (progress: {progress_val}%, expected: {expected_val:.1f}%).")

        return {
            "schedule_id": schedule_id,
            "insights": insights if insights else ["No major schedule deviations detected."]
        }