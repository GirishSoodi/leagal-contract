def grade_fn(state, env):
    try:
        return float(env.compute_score())
    except Exception:
        return 0.0


TASKS = [
    {
        "id": "easy",
        "description": "Detect high-risk clauses",
        "grader": grade_fn,   # ✅ NOT STRING
    },
    {
        "id": "medium",
        "description": "Detect risks and suggest edits",
        "grader": grade_fn,
    },
    {
        "id": "hard",
        "description": "Full contract review",
        "grader": grade_fn,
    },
]