import os

# Ensure generated folder exists
GEN_FOLDER = "gen"
os.makedirs(GEN_FOLDER, exist_ok=True)

def save_pddl(domain_str: str, problem_str: str, base_name: str):
    """
    Save the PDDL domain and problem file in the generated folder.
    """
    with open(f"{GEN_FOLDER}/{base_name}_domain.pddl", "w") as f:
        f.write(domain_str)

    with open(f"{GEN_FOLDER}/{base_name}_problem.pddl", "w") as f:
        f.write(problem_str)

def schedule_to_pddl(schedule_data):
    """
    Convert schedule data to a simple PDDL representation.
    """
    domain_str = "(define (domain construction))"
    problem_str = "(define (problem proj))"
    return domain_str, problem_str