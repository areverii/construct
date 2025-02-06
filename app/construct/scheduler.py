# construct/scheduler.py
import subprocess

def run_optic(domain_file: str, problem_file: str) -> str:
    """
    Calls the OPTIC planner with the given domain and problem files.
    Returns the stdout output from the planner.
    """
    cmd = ["optic", "-d", domain_file, "-p", problem_file]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout