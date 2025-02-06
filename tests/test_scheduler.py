# tests/test_scheduler.py
import os
import tempfile
import subprocess
from datetime import datetime
from typer.testing import CliRunner
import pytest
from sqlalchemy import text, delete, insert

# Import the function under test from our scheduler module.
from construct.scheduler import run_optic
# Import the main Typer app and database initializer and mapping table.
from construct.main import app
from construct.database import init_db, pddl_mappings_table

runner = CliRunner()

def fake_run(cmd, capture_output, text, check):
    """
    A fake subprocess.run implementation that simulates a successful OPTIC run.
    """
    class FakeCompletedProcess:
        def __init__(self, stdout):
            self.stdout = stdout
    # For our purposes, simply return a fixed output.
    return FakeCompletedProcess(stdout="Simulated OPTIC output: plan found.")

def test_run_optic(monkeypatch):
    # Monkey-patch subprocess.run to use our fake_run
    monkeypatch.setattr(subprocess, "run", fake_run)
    # Call run_optic with dummy file paths (contents are irrelevant in the fake)
    output = run_optic("dummy_domain.pddl", "dummy_problem.pddl")
    assert "Simulated OPTIC output" in output

def test_run_scheduler_cli(monkeypatch, tmp_path):
    """
    This test creates a temporary database and dummy PDDL files,
    inserts a mapping for a test schedule ID ("TEST123"), then invokes the
    run-scheduler CLI command and asserts that the simulated OPTIC output is printed.
    """
    # Create a temporary DB file.
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    engine = init_db(db_url=db_url)
    
    # Create dummy domain and problem files.
    domain_file = str(tmp_path / "dummy_domain.pddl")
    problem_file = str(tmp_path / "dummy_problem.pddl")
    with open(domain_file, "w") as f:
        f.write("(define (domain dummy))")
    with open(problem_file, "w") as f:
        f.write("(define (problem dummy))")
    
    # Insert a dummy mapping row.
    with engine.begin() as conn:
        conn.execute(
            delete(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "TEST123")
        )
        conn.execute(
            insert(pddl_mappings_table),
            {
                "schedule_id": "TEST123",
                "domain_file": domain_file,
                "problem_file": problem_file,
                "created_at": datetime.utcnow().isoformat()
            }
        )
    
    # Ensure that when main.init_db() is called, it returns our temporary engine.
    monkeypatch.setattr("construct.main.init_db", lambda db_url=None: engine)
    # Monkey-patch subprocess.run (used inside run_optic) to simulate OPTIC output.
    monkeypatch.setattr(subprocess, "run", fake_run)
    
    # Use Typer's CliRunner to invoke the run-scheduler command.
    result = runner.invoke(app, ["run-scheduler", "TEST123"])
    # Check that the output contains our simulated OPTIC output.
    assert "Simulated OPTIC output" in result.output