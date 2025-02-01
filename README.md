
Ingest a target schedule:
poetry run python construct ingest-schedule resources/test_1.xlsx --schedule-type target

Ingest an in-progress schedule:
poetry run construct ingest-schedule resources/test_1_progress_1.xlsx --schedule-type in-progress

Compare schedules:
poetry run construct compare-schedules [schedule_id]
    # test_1 project_id: 240001



EXAMPLE
ingest---

poetry run construct ingest-schedule resources/test_1.xlsx --schedule-type target                                                                                                        
poetry run construct ingest-schedule resources/test_1_progress_1.xlsx --schedule-type in-progress                                                                                    


set dates---

poetry run python -c "from construct.project_management import set_project_start_date; from construct.database import init_db; set_project_start_date(init_db(), '240001', '9/7/2023 8:00:00 AM')"

poetry run python -c "from construct.project_management import set_project_end_date; from construct.database import init_db; set_project_end_date(init_db(), '240001', '10/12/2023 5:00:00 PM')"

poetry run python -c "from construct.project_management import set_current_in_progress_date; from construct.database import init_db; set_current_in_progress_date(init_db(), '240001', '9/12/2023 11:00:00 AM')"

compare schedules---
poetry run construct compare-schedules 240001