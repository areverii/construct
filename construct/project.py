# construct/project.py
import os
import json
from datetime import datetime, timezone

def create_project(project_name: str, schedule_id: str, project_folder: str) -> tuple[str, str]:
    """
    Create a new project.
      - Creates (or reuses) the given project folder.
      - Writes a .cproj file (a JSON file with basic info) into that folder.
      - Creates a SQLite database file in the same folder.
    Returns a tuple: (project_file_path, db_file_path)
    """
    os.makedirs(project_folder, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_name = project_name.replace(" ", "_")
    project_file = os.path.join(project_folder, f"{safe_name}_{schedule_id}_{timestamp}.cproj")
    db_file = os.path.join(project_folder, f"{schedule_id}.db")
    
    project_data = {
        "project_name": project_name,
        "schedule_id": schedule_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "db_file": db_file,
        "project_folder": project_folder
    }
    with open(project_file, "w") as f:
        json.dump(project_data, f, indent=2)
    
    # (The DB file will be created by SQLAlchemy later, but we create an empty file here.)
    with open(db_file, "w") as f:
        f.write("")
    
    return project_file, db_file