# construct/models.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ScheduleRow(BaseModel):
    project_id: str
    project_name: str
    wbs_value: str
    task_id: str
    parent_id: str
    task_name: Optional[str] = None
    percent_done: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration: Optional[float] = None
    duration_unit: Optional[str] = None
    bl_start: Optional[datetime] = None
    bl_finish: Optional[datetime] = None
    crew_size: Optional[float] = None
    location_name: Optional[str] = None
    company_name: Optional[str] = None
    company_color: Optional[str] = None
    pull_plan: Optional[str] = None
    calendar_name: Optional[str] = None
    constraint_type: Optional[str] = None
    constraint_date: Optional[datetime] = None
    deadline_date: Optional[datetime] = None
    deadline_variance: Optional[float] = None
    p6_activity_id: Optional[str] = None
    notes: Optional[str] = None
    ordered_parent_index: Optional[int] = None
    p6_wbs_level: Optional[int] = None
    p6_wbs_guid: Optional[str] = None
    p6_wbs_parent_guid: Optional[str] = None
    date_and_time: Optional[datetime] = None

class ScheduleData(BaseModel):
    schedule_id: str
    tasks: List[ScheduleRow]
