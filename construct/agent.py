# construct/agent.py

from construct.models import ScheduleData

class ConstructionAgent:
    def __init__(self):
        pass

    def process_schedule(self, schedule_data: ScheduleData):
        return {
            "schedule_id": schedule_data.schedule_id,
            "project_name": schedule_data.tasks[0].project_name if schedule_data.tasks else None,
            "tasks": [task.model_dump(mode="json") for task in schedule_data.tasks],
        }