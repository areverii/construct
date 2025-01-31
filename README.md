
Ingest a target schedule:
poetry run python construct ingest-schedule resources/test_1.xlsx --schedule-type target

Ingest an in-progress schedule:
poetry run construct ingest-schedule resources/test_1_progress_1.xlsx --schedule-type in-progress

Compare schedules:
poetry run construct compare-schedules [schedule_id]
    # test_1 project_id: 240001