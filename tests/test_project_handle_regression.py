import os
import json

def test_project_handle_creation(tmp_path):
    """
    This test creates a temporary project folder and a dummy project handle file,
    then reads the file to ensure it contains the required keys ("db_file" and "project_folder")
    and that these paths exist on disk.
    """
    # Create a temporary project folder.
    project_dir = tmp_path / "TestProject"
    project_dir.mkdir()

    # Define file paths for a dummy database file and project handle.
    db_file = project_dir / "project.db"
    project_handle_file = project_dir / "project.cproj"

    # Create a dummy (or empty) database file.
    db_file.write_text("dummy database content")

    # Write a dummy project handle JSON file with required keys.
    project_handle_data = {
        "db_file": str(db_file),
        "project_folder": str(project_dir)
    }
    project_handle_file.write_text(json.dumps(project_handle_data))

    # Simulate how the API endpoint opens the project handle.
    with open(project_handle_file, "r") as f:
        loaded_data = json.load(f)

    # Assert the required keys exist.
    assert "db_file" in loaded_data, "Project handle missing 'db_file' key"
    assert "project_folder" in loaded_data, "Project handle missing 'project_folder' key"

    # Verify that the file paths exist.
    assert os.path.exists(loaded_data["db_file"]), "DB file does not exist on disk"
    assert os.path.isdir(loaded_data["project_folder"]), "Project folder does not exist on disk"