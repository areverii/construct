from construct.database import projects_table, tasks_table, dependencies_table
from sqlalchemy import select

class ConstructionAgent:
    def __init__(self, engine):
        self.engine = engine

    def fetch_tasks(self, schedule_id: str, schedule_type: str):
        """
        Fetches all tasks for a given schedule.
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                select(tasks_table)
                .where(tasks_table.c.schedule_id == schedule_id)
            ).fetchall()

            return [dict(row) for row in result]

    def analyze_progress(self, schedule_id: str):
        """
        Compare in-progress schedule with target schedule.
        """
        target_tasks = self.fetch_tasks(schedule_id, "target")
        progress_tasks = self.fetch_tasks(schedule_id, "in-progress")

        insights = []
        for target, progress in zip(target_tasks, progress_tasks):
            if progress["task_id"] == target["task_id"]:
                if progress["percent_done"] < target["percent_done"]:
                    insights.append(f"Task '{progress['task_name']}' is behind schedule.")
                elif progress["percent_done"] > target["percent_done"]:
                    insights.append(f"Task '{progress['task_name']}' is ahead of schedule.")

        return {"schedule_id": schedule_id, "insights": insights}