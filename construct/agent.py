from construct.models import ScheduleData
from construct.database import schedule_table
from sqlalchemy import select

class ConstructionAgent:
    def __init__(self, engine):
        self.engine = engine

    def fetch_schedule(self, schedule_id: str, schedule_type: str) -> ScheduleData:
        """
        Fetch a schedule (target or in-progress) from the database.
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                select(schedule_table.c.raw_data)
                .where(schedule_table.c.name == schedule_id)
                .where(schedule_table.c.type == schedule_type)
            ).fetchone()

            if not result:
                return None  # Schedule not found

            return ScheduleData.parse_raw(result[0])  # Load JSON as ScheduleData

    def analyze_progress(self, schedule_id: str):
        """
        Compare the target schedule with the in-progress schedule.
        """
        target = self.fetch_schedule(schedule_id, "target")
        progress = self.fetch_schedule(schedule_id, "in-progress")

        if not target or not progress:
            return {"error": "Target or in-progress schedule not found"}

        insights = []
        for target_task, progress_task in zip(target.tasks, progress.tasks):
            if target_task.task_id == progress_task.task_id:
                # ✅ Handle None values by treating missing progress as 0.0
                target_percent_done = target_task.percent_done if target_task.percent_done is not None else 0.0
                progress_percent_done = progress_task.percent_done if progress_task.percent_done is not None else 0.0

                if progress_percent_done < target_percent_done:
                    insights.append(f"Task '{progress_task.task_name}' is behind schedule (progress: {progress_percent_done}%, expected: {target_percent_done}%).")
                elif progress_percent_done > target_percent_done:
                    insights.append(f"Task '{progress_task.task_name}' is ahead of schedule (progress: {progress_percent_done}%, expected: {target_percent_done}%).")
        
        return {
            "schedule_id": schedule_id,
            "insights": insights if insights else ["No major schedule deviations detected."]
        }

    def process_schedule(self, schedule_data: ScheduleData):
        """
        Processes and structures the schedule data.
        """
        return {
            "schedule_id": schedule_data.schedule_id,
            "project_name": schedule_data.tasks[0].project_name if schedule_data.tasks else None,
            "tasks": [task.model_dump(mode="json") for task in schedule_data.tasks],
        }