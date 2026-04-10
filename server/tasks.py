def grade_fn(state, env):
    try:
        visited_ratio = len(env.visited) / max(len(env.clauses), 1)

        if env.task_type == "easy":
            score = visited_ratio

        elif env.task_type == "medium":
            score = visited_ratio + (len(env.edited) * 0.1)

        elif env.task_type == "hard":
            score = visited_ratio + (len(env.edited) * 0.1) + (len(env.flagged) * 0.1)

        else:
            score = visited_ratio

        # 🔥 CRITICAL FIX: ensure non-zero baseline
        return float(max(min(score, 1.0), 0.1))

    except Exception:
        return 0.1