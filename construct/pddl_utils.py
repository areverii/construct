# construct/pddl_utils.py

# minimal pddl generation

def schedule_to_pddl(schedule_data) -> str:
    # build domain/problem strings
    # keep it very simplistic here
    domain_str = "(define (domain construction))"  # placeholder
    problem_str = "(define (problem proj))"        # placeholder
    return domain_str, problem_str

def save_pddl(domain_str: str, problem_str: str, base_name: str = "construction"):
    with open(f"{base_name}_domain.pddl", "w") as f:
        f.write(domain_str)
    with open(f"{base_name}_problem.pddl", "w") as f:
        f.write(problem_str)