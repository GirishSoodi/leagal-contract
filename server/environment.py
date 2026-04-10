from uuid import uuid4
import random
import json
import os
from typing import Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from legalcontractreview.models import (
    LegalContractReviewAction,
    LegalContractReviewObservation,
)

# 🔥 IMPORT GRADER (NEW)
from legalcontractreview.tasks import grade_fn


class LegalcontractreviewEnvironment(Environment):

    SUPPORTS_CONCURRENT_SESSIONS = True

    # 🔥 CRITICAL FIX: REGISTER TASK NAMES
    AVAILABLE_TASKS = ["easy", "medium", "hard"]

    def __init__(self):
        print("🔍 Initializing LegalcontractreviewEnvironment...")

        DATA_PATH = os.getenv("DATA_PATH")

        if DATA_PATH:
            print(f"📦 Using DATA_PATH from environment: {DATA_PATH}")
        else:
            pkg_path = os.path.join(os.path.dirname(__file__), "processed", "contracts.json")
            cwd_path = os.path.join(os.getcwd(), "server", "processed", "contracts.json")

            if os.path.exists(pkg_path):
                DATA_PATH = pkg_path
                print(f"📦 Found dataset in package path: {DATA_PATH}")
            elif os.path.exists(cwd_path):
                DATA_PATH = cwd_path
                print(f"📦 Found dataset in CWD path: {DATA_PATH}")
            else:
                DATA_PATH = pkg_path
                print("⚠️ Dataset not found, will fallback safely")

        try:
            if not os.path.exists(DATA_PATH):
                raise FileNotFoundError("Dataset file not found")

            with open(DATA_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()

                if not content:
                    raise ValueError("Dataset file is empty")

                self.dataset = json.loads(content)

            print(f"✅ Loaded dataset with {len(self.dataset)} contracts")

        except Exception as e:
            print("🔥 DATA LOAD FAILED:", e)

            self.dataset = [{
                "contract_id": "fallback",
                "clauses": [
                    {"id": "1", "text": "This agreement is valid."},
                    {"id": "2", "text": "No termination clause provided."}
                ],
                "labels": {"1": "general", "2": "termination"},
                "risk_levels": {"1": "low", "2": "high"},
                "playbook_flags": {"1": "ok", "2": "review"},
                "missing_clauses": ["termination"]
            }]

        self._state = State(episode_id=str(uuid4()), step_count=0)

    def _normalize_key(self, x):
        return str(x).strip().lower()

    # =====================================================
    # 🔥 FIXED: USE IMPORTED GRADER
    # =====================================================
    def get_tasks(self):
        from openenv.core.env_server.types import Task

        return [
            Task(id="easy", description="Detect high-risk clauses", grader=grade_fn),
            Task(id="medium", description="Detect risks and suggest edits", grader=grade_fn),
            Task(id="hard", description="Full contract review", grader=grade_fn),
        ]

    # =====================================================
    def reset(self, task_id: Optional[str] = None):

        self._state = State(episode_id=str(uuid4()), step_count=0)

        if task_id in ["easy", "medium", "hard"]:
            self.task_type = task_id
        else:
            self.task_type = "easy"

        self.contract = random.choice(self.dataset)

        self.goal = {
            "easy": "Detect high-risk clauses",
            "medium": "Detect risks and suggest edits",
            "hard": "Full contract review"
        }[self.task_type]

        self.gt_labels = {self._normalize_key(k): v for k, v in self.contract["labels"].items()}
        self.gt_risk = {self._normalize_key(k): v for k, v in self.contract["risk_levels"].items()}
        self.gt_playbook = {self._normalize_key(k): v for k, v in self.contract["playbook_flags"].items()}
        self.gt_missing = [self._normalize_key(x) for x in self.contract.get("missing_clauses", [])]
        self.initial_gt_missing = list(self.gt_missing)

        self.clauses = self.contract["clauses"]

        self.clause_map = {
            self._normalize_key(c["id"]): i
            for i, c in enumerate(self.clauses)
        }

        self.index = 0
        self.steps = 0

        self.flagged = set()
        self.edited = set()
        self.pred_missing = []
        self.visited = set()

        self.last_action = None
        self.same_action_count = 0

        return self._obs(0.0, False)

    # =====================================================
    def step(self, action: LegalContractReviewAction):

        self._state.step_count += 1
        self.steps += 1

        reward = 0.0
        done = False

        if action.action_type == self.last_action:
            self.same_action_count += 1
        else:
            self.same_action_count = 0

        self.last_action = action.action_type

        if self.same_action_count > 3:
            reward -= 0.5

        if action.clause_id is not None:
            cid_input = self._normalize_key(action.clause_id)
            if cid_input in self.clause_map:
                self.index = self.clause_map[cid_input]

        clause = self.clauses[self.index]
        cid = self._normalize_key(clause["id"])

        if cid not in self.visited:
            reward += 0.1
            self.visited.add(cid)
        else:
            reward -= 0.1

        true_risk = self.gt_risk.get(cid, "low")
        true_flag = self.gt_playbook.get(cid, "ok")

        if action.action_type == "flag_risk":
            reward += 1.5 if true_risk == "high" else -1.0

        elif action.action_type == "suggest_edit":
            if true_flag in ["violation", "review"] and action.content:
                reward += 2.0
            else:
                reward -= 0.5

        elif action.action_type == "next_clause":
            if self.index < len(self.clauses) - 1:
                self.index += 1

        elif action.action_type == "finish_review":
            done = True
            score = self.compute_score()
            reward += 5.0 if score > 0.7 else -1.0

        return self._obs(reward, done)

    # =====================================================
    def compute_score(self):
        base = len(self.visited) / max(len(self.clauses), 1)
        return max(base, 0.1)

    # =====================================================
    def _obs(self, reward, done):

        clause = self.clauses[self.index].copy()
        cid = self._normalize_key(clause["id"])

        clause["type"] = self.gt_labels.get(cid, "unknown")

        return LegalContractReviewObservation(
            contract_id=self.contract["contract_id"],
            contract_type="general",
            party_role="client",

            current_clause=clause,
            clause_index=self.index,
            total_clauses=len(self.clauses),

            issues_found=[],
            time_step=self.steps,

            reward=reward,
            done=done,

            metadata={
                "task_type": self.task_type,
                "goal": self.goal,
                "score": self.compute_score(),
            }
        )

    @property
    def state(self):
        return self._state