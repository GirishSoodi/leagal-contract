def grade_fn(state, env):
    try:
        return float(env.compute_score())
    except Exception:
        return 0.0