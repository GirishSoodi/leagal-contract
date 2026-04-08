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


class LegalcontractreviewEnvironment(Environment):

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):

        DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "processed", "contracts.json")
        DATA_PATH = os.getenv("DATA_PATH", DEFAULT_PATH)

        if not os.path.exists(DATA_PATH):
            LOCAL_FALLBACK = os.path.join(os.getcwd(), "server", "processed", "contracts.json")
            if os.path.exists(LOCAL_FALLBACK):
                DATA_PATH = LOCAL_FALLBACK
            else:
                raise FileNotFoundError(f"Dataset not found")

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            self.dataset = json.load(f)

        print(f"✅ Loaded dataset with {len(self.dataset)} contracts")

        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.reset()

    # =====================================================
    # 🔧 NORMALIZATION
    # =====================================================
    def _normalize_key(self, x):
        return str(x).strip().lower()

    # =====================================================
    # 🔁 RESET
    # =====================================================
    def reset(self, task_id: Optional[str] = None):

        self._state = State(episode_id=str(uuid4()), step_count=0)

        self.task_type = task_id if task_id in ["easy", "medium", "hard"] else random.choice(["easy", "medium", "hard"])

        self.contract = random.choice(self.dataset)

        self.goal = {
            "easy": "Detect high-risk clauses",
            "medium": "Detect risks and suggest edits",
            "hard": "Full contract review"
        }[self.task_type]

        # ✅ Normalize GT
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

        # 🔥 Anti-spam tracking
        self.last_action = None
        self.same_action_count = 0

        return self._obs(0.0, False)

    # =====================================================
    # 🎯 STEP (FINAL FIXED)
    # =====================================================
    def step(self, action: LegalContractReviewAction):

        self._state.step_count += 1
        self.steps += 1

        reward = 0.0
        done = False

        # =========================
        # 🔥 Anti-spam
        # =========================
        if action.action_type == self.last_action:
            self.same_action_count += 1
        else:
            self.same_action_count = 0

        self.last_action = action.action_type

        if self.same_action_count > 3:
            reward -= 0.5

        # =========================
        # 🔥 Clause jump
        # =========================
        if action.clause_id is not None:
            cid_input = self._normalize_key(action.clause_id)

            if cid_input in self.clause_map:
                self.index = self.clause_map[cid_input]

        # =========================
        # Current clause
        # =========================
        clause = self.clauses[self.index]
        cid = self._normalize_key(clause["id"])

        # =========================
        # 🔥 Exploration reward
        # =========================
        if cid not in self.visited:
            reward += 0.1
            self.visited.add(cid)
        else:
            reward -= 0.1

        true_risk = self.gt_risk.get(cid, "low")
        true_flag = self.gt_playbook.get(cid, "ok")

        # =========================
        # ⚡ Actions
        # =========================
        if action.action_type == "flag_risk":
            if true_risk == "high":
                reward += 1.5
                self.flagged.add(cid)
            elif true_risk == "medium":
                reward += 1.0
                self.flagged.add(cid)
            else:
                reward -= 1.0

        elif action.action_type == "mark_safe":
            if true_risk == "high":
                reward -= 2.0
            elif true_risk == "medium":
                reward -= 0.5
            else:
                reward += 0.1

        elif action.action_type == "suggest_edit":
            if true_flag in ["violation", "review"]:
                if action.content and len(action.content.strip()) > 20:
                    reward += 2.0
                    self.edited.add(cid)
                else:
                    reward -= 0.5
            else:
                reward -= 0.5

        elif action.action_type == "add_clause":
            content = self._normalize_key(action.content)

            if content in self.gt_missing:
                reward += 3.0
                self.gt_missing.remove(content)
                self.pred_missing.append(content)
            else:
                reward -= 1.0

        elif action.action_type == "next_clause":
            if self.index < len(self.clauses) - 1:
                self.index += 1
            else:
                reward -= 0.2

        elif action.action_type == "finish_review":
            done = True
            score = self.compute_score()

            if score > 0.7:
                reward += 5.0
            elif score > 0.4:
                reward += 2.0
            else:
                reward -= 1.0

        return self._obs(reward, done)

    # =====================================================
    # 🧠 SCORING
    # =====================================================
    def compute_score(self):

        if self.task_type == "easy":
            gt_high = {k for k, v in self.gt_risk.items() if v == "high"}
            correct = self.flagged.intersection(gt_high)
            return len(correct) / max(len(gt_high), 1)

        elif self.task_type == "medium":
            gt_risk = {k for k, v in self.gt_risk.items() if v in ["high", "medium"]}
            gt_edit = {k for k, v in self.gt_playbook.items() if v in ["violation", "review"]}

            risk_score = len(self.flagged.intersection(gt_risk)) / max(len(gt_risk), 1)
            edit_score = len(self.edited.intersection(gt_edit)) / max(len(gt_edit), 1)

            return 0.5 * risk_score + 0.5 * edit_score

        elif self.task_type == "hard":
            gt_risk = {k for k, v in self.gt_risk.items() if v in ["high", "medium"]}
            gt_edit = {k for k, v in self.gt_playbook.items() if v in ["violation", "review"]}

            risk_score = len(self.flagged.intersection(gt_risk)) / max(len(gt_risk), 1)
            edit_score = len(self.edited.intersection(gt_edit)) / max(len(gt_edit), 1)

            missing_score = len(self.pred_missing) / max(len(self.initial_gt_missing), 1)

            return 0.3 * risk_score + 0.3 * edit_score + 0.4 * missing_score

        return 0.0

    # =====================================================
    # 👁 OBS
    # =====================================================
    def _obs(self, reward, done):

        clause = self.clauses[self.index].copy()
        cid = self._normalize_key(clause["id"])

        clause["type"] = self.gt_labels.get(cid, "unknown")

        issues_found = [
            {
                "clause_id": cid,
                "risk": self.gt_risk.get(cid, "low"),
                "type": self.gt_labels.get(cid, "unknown")
            }
            for cid in self.flagged
        ]

        score = self.compute_score()

        return LegalContractReviewObservation(
            contract_id=self.contract["contract_id"],
            contract_type="general",
            party_role="client",

            current_clause=clause,
            clause_index=self.index,
            total_clauses=len(self.clauses),

            issues_found=issues_found,
            time_step=self.steps,

            reward=reward,
            done=done,

            metadata={
                "task_type": self.task_type,
                "goal": self.goal,
                "score": score,
                "visited_count": len(self.visited),
            }
        )

    @property
    def state(self):
        return self._state