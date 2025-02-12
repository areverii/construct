# Setup and Usage

## prerequisites
- install docker
- install docker compose
- clone this repository

## setup
1. run `./startup.sh` to build and start the docker containers.
2. confirm the api is running by checking the logs:  
   ```bash
   docker compose logs -f
   ```

## testing
  ```bash
  ./test.sh
  ```

## verify api
  ```bash
  curl http://localhost:8000/
  ```


DEPRECATED (to be removed/revised)
----------

## 1. Installation & Setup

### Install Dependencies

```bash
poetry install
```

## 2. Usage

### Initialize the Database

```bash
poetry run python -c "from construct.database import init_db; init_db()"
```

### Ingest a Target Schedule

```bash
poetry run python -c "
from construct.database import init_db;
from construct.ingestion import ingest_schedule_data;
engine = init_db();
ingest_schedule_data(
    file_path='resources/test_1.xlsx',
    schedule_id='240001',
    schedule_type='target',
    engine=engine
)
"
```

This reads the Excel file and:

* Inserts/updates a projects row where (schedule_id='240001', schedule_type='target').
* Inserts/updates tasks that fill the baseline columns (bl_start, bl_finish) if present.
* (If your Excel columns are instead named start_date/end_date for target tasks, the ingestion code can treat them as baseline columns as well.)

### Ingest an In-Progress Schedule

```bash
poetry run python -c "
from construct.database import init_db;
from construct.ingestion import ingest_schedule_data;
engine = init_db();
ingest_schedule_data(
    file_path='resources/test_1_progress_1.xlsx',
    schedule_id='240001',
    schedule_type='in-progress',
    engine=engine
)
"
```

This creates/updates (schedule_id='240001', schedule_type='in-progress'), populating the actual columns (start_date, end_date) plus percent_done.

### Set Current In-Progress Date

```bash
poetry run python -c "
from construct.project_management import set_current_in_progress_date;
from construct.database import init_db;
engine = init_db();
set_current_in_progress_date(
    engine=engine,
    schedule_id='240001',
    in_progress_date='2024-02-01 08:00:00'
)
"
```

### Run Analysis

```bash
poetry run python -c "
import json
from construct.database import init_db;
from construct.agent import ConstructionAgent;

engine = init_db()
agent = ConstructionAgent(engine)
result = agent.analyze_progress('240001')
print(json.dumps(result, indent=2))
"
```

### Example Output

```bash
{
  "schedule_id": "240001",
  "insights": [
    "Task 'X' is behind schedule (progress: 10.0%, expected: 25.0%).",
    "Task 'Y' is ahead of schedule (progress: 80.0%, expected: 60.0%)."
  ]
}
```
