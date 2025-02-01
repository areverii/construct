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
            print(f"DEBUG: Fetching tasks for schedule_id={schedule_id}, schedule_type={schedule_type}")  # Debugging output
            
            result = conn.execute(
                select(tasks_table)
                .where(tasks_table.c.schedule_id == schedule_id)
            ).fetchall()

            print(f"DEBUG: Query result: {result}")  # debugging output

            if not result:
                print(f"DEBUG: No tasks found for schedule {schedule_id} ({schedule_type})")
                return []

            return [dict(row._mapping) for row in result]  # fix TypeError by using `_mapping`

    def analyze_progress(self, schedule_id: str):
        """
        Compare the target schedule with the in-progress schedule.
        """
        target_tasks = self.fetch_tasks(schedule_id, "target")
        progress_tasks = self.fetch_tasks(schedule_id, "in-progress")

        if not target_tasks or not progress_tasks:
            return {"error": "Target or in-progress schedule not found"}

        insights = []
        for target, progress in zip(target_tasks, progress_tasks):
            if target["task_id"] == progress["task_id"]:
                # ✅ Handle None values by treating missing progress as 0.0
                target_percent_done = target["percent_done"] if target["percent_done"] is not None else 0.0
                progress_percent_done = progress["percent_done"] if progress["percent_done"] is not None else 0.0

                if progress_percent_done < target_percent_done:
                    insights.append(f"Task '{progress['task_name']}' is behind schedule (progress: {progress_percent_done}%, expected: {target_percent_done}%).")
                elif progress_percent_done > target_percent_done:
                    insights.append(f"Task '{progress['task_name']}' is ahead of schedule (progress: {progress_percent_done}%, expected: {target_percent_done}%).")

        return {
            "schedule_id": schedule_id,
            "insights": insights if insights else ["No major schedule deviations detected."]
        }