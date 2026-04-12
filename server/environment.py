from uuid import uuid4
import random
import json
import os
from typing import Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import (
    LegalContractReviewAction,
    LegalContractReviewObservation,
)


class LegalContractReviewEnv(Environment):

    SUPPORTS_CONCURRENT_SESSIONS = True

    TASKS = [
        {"id": "easy", "description": "Find high-risk clauses"},
        {"id": "medium", "description": "Find high-risk + suggest edits"},
        {"id": "hard", "description": "Full contract review"}
    ]

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)

        DATA_PATH = os.path.join(os.path.dirname(__file__), "processed", "contracts.json")

        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                self.dataset = json.load(f)
        except:
            self.dataset = [{
                "contract_id": "fallback",
                "clauses": [
                    {"id": "1", "text": "No termination clause provided."},
                    {"id": "2", "text": "Unlimited liability clause."}
                ],
                "labels": {"1": "termination", "2": "liability"},
                "risk_levels": {"1": "high", "2": "high"},
                "playbook_flags": {"1": "review", "2": "violation"},
                "missing_clauses": ["termination"]
            }]

        self.current = None
        self.task_type = "easy"

    def get_tasks(self):
        return self.TASKS

    # =====================================================
    def _get_clause_with_type(self, clause):
        cid = str(clause["id"])
        label = self.current.get("labels", {}).get(cid, "general")

        return {
            "id": clause["id"],
            "text": clause["text"],
            "type": label
        }

    # =====================================================
    def reset(self, task_id: Optional[str] = None):

        self._state = State(episode_id=str(uuid4()), step_count=0)

        if task_id in ["easy", "medium", "hard"]:
            self.task_type = task_id
        else:
            self.task_type = "easy"

        self.current = random.choice(self.dataset)

        self.flagged = set()
        self.edited = set()
        self.pred_missing = set()

        self.index = 0

        clause = self._get_clause_with_type(self.current["clauses"][0])

        return LegalContractReviewObservation(
            contract_id=self.current["contract_id"],
            contract_type="general",
            party_role="client",

            current_clause=clause,
            clause_index=0,
            total_clauses=len(self.current["clauses"]),

            issues_found=[],
            time_step=0,

            reward=0.0,
            done=False,

            metadata={
                "task_type": self.task_type,
                "instruction": self._get_instruction()
            }
        )

    # =====================================================
    def step(self, action: LegalContractReviewAction):

        self._state.step_count += 1
        done = False
        reward = 0.0

        clause = self.current["clauses"][self.index]
        cid = str(clause["id"])

        # -------- TRACK ACTIONS --------
        if action.action_type == "flag_risk":
            self.flagged.add(cid)

        elif action.action_type == "suggest_edit":
            self.edited.add(cid)

        elif action.action_type == "next_clause":
            if self.index < len(self.current["clauses"]) - 1:
                self.index += 1

        elif action.action_type == "finish_review":
            done = True
            reward = self._compute_score()

        clause = self._get_clause_with_type(self.current["clauses"][self.index])

        return LegalContractReviewObservation(
            contract_id=self.current["contract_id"],
            contract_type="general",
            party_role="client",

            current_clause=clause,
            clause_index=self.index,
            total_clauses=len(self.current["clauses"]),

            issues_found=[],
            time_step=self._state.step_count,

            reward=float(reward),
            done=done,

            metadata={
                "task_type": self.task_type,
                "score": float(reward)
            }
        )

    # =====================================================
    def _compute_score(self):

        gt_risk = {
            str(cid): risk
            for cid, risk in self.current.get("risk_levels", {}).items()
        }

        gt_missing = set([
            str(x).lower()
            for x in self.current.get("missing_clauses", [])
        ])

        # EASY
        if self.task_type == "easy":
            gt_set = set([cid for cid, r in gt_risk.items() if r == "high"])
            return self._f1(self.flagged, gt_set)

        # MEDIUM
        elif self.task_type == "medium":
            gt_flagged = set([cid for cid, r in gt_risk.items() if r == "high"])
            gt_edits = set([
                cid for cid, flag in self.current.get("playbook_flags", {}).items()
                if flag in ["review", "violation"]
            ])

            score_flag = self._f1(self.flagged, gt_flagged)
            score_edit = self._f1(self.edited, gt_edits)

            return 0.5 * score_flag + 0.5 * score_edit

        # HARD
        elif self.task_type == "hard":
            gt_flagged = set([cid for cid, r in gt_risk.items() if r == "high"])

            score_flag = self._f1(self.flagged, gt_flagged)
            score_missing = self._f1(self.pred_missing, gt_missing)

            return 0.5 * score_flag + 0.5 * score_missing

        return 0.0

    # =====================================================
    def _f1(self, pred: set, gt: set):

        if len(gt) == 0:
            return 1.0

        if len(pred) == 0:
            return 0.0

        precision = len(pred & gt) / len(pred)
        recall = len(pred & gt) / len(gt)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    # =====================================================
    def _get_instruction(self):

        if self.task_type == "easy":
            return "Flag high-risk clauses"

        elif self.task_type == "medium":
            return "Flag risks and suggest edits"

        elif self.task_type == "hard":
            return "Full contract review"

    # =====================================================
    @property
    def state(self):
        return self._state