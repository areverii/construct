from datetime import datetime
from sqlalchemy import select
from construct.database import projects_table, tasks_table
from construct.utils import parse_user_date

class ConstructionAgent:
    def __init__(self, engine):
        self.engine = engine

    def fetch_tasks(self, schedule_id: str, schedule_type: str):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(tasks_table)
                .where(tasks_table.c.schedule_id == schedule_id)
                .where(tasks_table.c.schedule_type == schedule_type)
            ).fetchall()
        return [dict(r._mapping) for r in rows]

    def compute_expected_percent_done(self, bl_start_str: str, bl_finish_str: str, current_day: datetime) -> float:
        start_dt = parse_user_date(bl_start_str)
        finish_dt = parse_user_date(bl_finish_str)
        if not start_dt or not finish_dt:
            return 0.0
        if current_day < start_dt:
            return 0.0
        elif current_day >= finish_dt:
            return 100.0
        else:
            total_seconds = (finish_dt - start_dt).total_seconds()
            elapsed_seconds = (current_day - start_dt).total_seconds()
            if total_seconds <= 0:
                return 100.0
            fraction = elapsed_seconds / total_seconds
            return min(100.0, max(0.0, fraction * 100.0))

    def analyze_progress(self, schedule_id: str):
        target_tasks = self.fetch_tasks(schedule_id, "target")
        progress_tasks = self.fetch_tasks(schedule_id, "in-progress")
        if not target_tasks or not progress_tasks:
            return {"error": "Target or in-progress schedule not found"}
        with self.engine.connect() as conn:
            row = conn.execute(
                select(projects_table.c.current_in_progress_date)
                .where(projects_table.c.schedule_id == schedule_id)
                .where(projects_table.c.schedule_type == "target")
            ).fetchone()
        current_str = row[0] if row else None
        current_day = parse_user_date(current_str) or datetime.utcnow()
        target_dict = {t["task_id"]: t for t in target_tasks}
        progress_dict = {t["task_id"]: t for t in progress_tasks}
        insights = []
        for tid, ttarget in target_dict.items():
            if tid not in progress_dict:
                continue
            tprogress = progress_dict[tid]
            actual_progress = tprogress.get("percent_done") or 0.0
            expected_val = self.compute_expected_percent_done(
                ttarget.get("bl_start"),
                ttarget.get("bl_finish"),
                current_day
            )
            if actual_progress < expected_val:
                insights.append(
                    f"Task '{tprogress['task_name']}' is behind schedule (progress: {actual_progress}%, expected: {expected_val:.1f}%)."
                )
            elif actual_progress > expected_val:
                insights.append(
                    f"Task '{tprogress['task_name']}' is ahead of schedule (progress: {actual_progress}%, expected: {expected_val:.1f}%)."
                )
        return {
            "schedule_id": schedule_id,
            "insights": insights if insights else ["no major schedule deviations detected."]
        }