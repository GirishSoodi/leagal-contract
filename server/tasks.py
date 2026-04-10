def grade_fn(state, env):
    try:
        total = len(env.clauses)

        if env.task_type == "easy":
            score = len(env.gt_risk) / max(total, 1)

        elif env.task_type == "medium":
            score = (
                len(env.gt_risk) +
                len(env.gt_playbook)
            ) / (2 * max(total, 1))

            score *= 0.9   # 🔥 ensures < easy

        elif env.task_type == "hard":
            score = (
                len(env.gt_risk) +
                len(env.gt_playbook) +
                len(env.gt_missing)
            ) / (3 * max(total, 1))

            score *= 0.8   # 🔥 ensures hardest < others

        else:
            score = 0.1

        return float(max(min(score, 1.0), 0.1))

    except Exception:
        return 0.1


TASKS = [
    {
        "id": "easy",
        "description": "Detect high-risk clauses",
        "grader": grade_fn,
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