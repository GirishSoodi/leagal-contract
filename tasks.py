from openenv.core.env_server.types import Task
from .graders import easy_grader, medium_grader, hard_grader


TASKS = [
    Task(id="easy", grader=easy_grader, description="Detect high-risk clauses"),
    Task(id="medium", grader=medium_grader, description="Detect risks and suggest edits"),
    Task(id="hard", grader=hard_grader, description="Full contract review"),
]

