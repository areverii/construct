# # tests/test_scheduler_actual.py
# import os
# import stat
# import subprocess
# import tempfile
# from datetime import datetime
# from typer.testing import CliRunner
# import pytest

# from construct.scheduler import run_optic
# from construct.main import app
# from construct.database import init_db, pddl_mappings_table
# from sqlalchemy import delete, insert, text

# runner = CliRunner()

# @pytest.fixture
# def dummy_optic(tmp_path, monkeypatch):
#     """
#     Create a dummy 'optic' executable that simulates the OPTIC planner.
#     It simply prints a known message to stdout.
#     """
#     dummy_exe = tmp_path / "optic"
#     dummy_exe.write_text(
#         "#!/usr/bin/env python3\n"
#         "print('Dummy OPTIC plan: Optimal schedule computed.')\n"
#     )
#     # Make the file executable.
#     dummy_exe.chmod(dummy_exe.stat().st_mode | stat.S_IEXEC)
#     # Prepend the directory with our dummy 'optic' to the PATH.
#     monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.getenv('PATH', '')}")
#     return dummy_exe

# def test_run_optic_actual(dummy_optic):
#     """
#     Test the scheduler integration by calling run_optic with dummy PDDL files.
#     """
#     # Create temporary dummy domain and problem files.
#     with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="_domain.pddl") as dom_file:
#         dom_file.write("(define (domain construction))")
#         dom_path = dom_file.name
#     with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="_problem.pddl") as prob_file:
#         prob_file.write("(define (problem proj_dummy))")
#         prob_path = prob_file.name

#     try:
#         output = run_optic(dom_path, prob_path)
#         assert "Dummy OPTIC plan" in output
#     finally:
#         os.unlink(dom_path)
#         os.unlink(prob_path)

# def test_run_scheduler_cli_actual(dummy_optic, tmp_path, monkeypatch):
#     """
#     End-to-end test that creates a temporary database with a dummy PDDL mapping,
#     then calls the run-scheduler CLI command and asserts that the dummy OPTIC output is returned.
#     """
#     # Create a temporary database file.
#     db_file = tmp_path / "test.db"
#     db_url = f"sqlite:///{db_file}"
#     engine = init_db(db_url=db_url)
    
#     # Create dummy domain and problem files in the temporary directory.
#     domain_file = str(tmp_path / "dummy_domain.pddl")
#     problem_file = str(tmp_path / "dummy_problem.pddl")
#     with open(domain_file, "w") as f:
#         f.write("(define (domain construction))")
#     with open(problem_file, "w") as f:
#         f.write("(define (problem proj_dummy))")
    
#     # Insert a dummy PDDL mapping row for schedule "DUMMY123".
#     with engine.begin() as conn:
#         conn.execute(delete(pddl_mappings_table).where(pddl_mappings_table.c.schedule_id == "DUMMY123"))
#         conn.execute(
#             insert(pddl_mappings_table),
#             {
#                 "schedule_id": "DUMMY123",
#                 "domain_file": domain_file,
#                 "problem_file": problem_file,
#                 "created_at": datetime.utcnow().isoformat()
#             }
#         )
    
#     # Override the init_db function in our main module so that when run-scheduler is invoked,
#     # it uses our temporary engine.
#     monkeypatch.setattr("construct.main.init_db", lambda db_url=None: engine)
    
#     # Use Typer's CliRunner to invoke the "run-scheduler" command.
#     result = runner.invoke(app, ["run-scheduler", "DUMMY123"])
#     assert "Dummy OPTIC plan" in result.output