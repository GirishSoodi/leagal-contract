# legalcontractreview/tasks.py

def grade_easy(pred, gt):
    gt_high = {k for k, v in gt["risk"].items() if v == "high"}
    flagged = set(pred.get("flagged", []))

    correct = len(flagged & gt_high)
    precision = correct / max(len(flagged), 1)
    recall = correct / max(len(gt_high), 1)

    return (precision + recall) / 2


def grade_medium(pred, gt):
    gt_high = {k for k, v in gt["risk"].items() if v == "high"}
    gt_review = {k for k, v in gt["playbook"].items() if v in ["review", "violation"]}

    flagged = set(pred.get("flagged", []))
    edited = set(pred.get("edited", []))

    risk_score = len(flagged & gt_high) / max(len(gt_high), 1)
    edit_score = len(edited & gt_review) / max(len(gt_review), 1)

    return 0.5 * risk_score + 0.5 * edit_score


def grade_hard(pred, gt):
    gt_high = {k for k, v in gt["risk"].items() if v == "high"}
    gt_review = {k for k, v in gt["playbook"].items() if v in ["review", "violation"]}
    gt_missing = set(gt["missing"])

    flagged = set(pred.get("flagged", []))
    edited = set(pred.get("edited", []))
    missing = set(pred.get("missing", []))

    risk_score = len(flagged & gt_high) / max(len(gt_high), 1)
    edit_score = len(edited & gt_review) / max(len(gt_review), 1)
    missing_score = len(missing & gt_missing) / max(len(gt_missing), 1)

    return 0.4 * risk_score + 0.3 * edit_score + 0.3 * missing_score


TASKS = [
    {
        "id": "easy",
        "description": "Detect high-risk clauses",
        "grader": "graders:easy_grader",
    },
    {
        "id": "medium",
        "description": "Detect risks and suggest edits",
        "grader": "graders:medium_grader",
    },
    {
        "id": "hard",
        "description": "Full contract review",
        "grader": "graders:hard_grader",
    },
]