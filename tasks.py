# NO imports from openenv needed

def grade_fn(state, env):
    try:
        return float(env.compute_score())
    except Exception:
        return 0.0


TASKS = {
    "easy": {
        "description": "Detect high-risk clauses",
        "grader": grade_fn,
    },
    "medium": {
        "description": "Detect risks and suggest edits",
        "grader": grade_fn,
    },
    "hard": {
        "description": "Full contract review",
        "grader": grade_fn,
    },
}

