# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Data models for the LegalContractReview Environment.
"""

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, List, Dict


# -------------------------------
# Clause Model (type-safe)
# -------------------------------
class Clause(BaseModel):
    """Represents a contract clause."""

    id: str = Field(..., description="Clause identifier")
    type: str = Field(..., description="Clause type (e.g., liability, payment)")
    text: str = Field(..., description="Clause content")
    severity: Optional[str] = Field(
        default=None,
        description="Risk severity: low / medium / high"
    )


# -------------------------------
# Action Model
# -------------------------------
class LegalContractReviewAction(Action):
    """Action representing a decision in contract review."""

    action_type: Literal[
        "flag_risk",
        "mark_safe",
        "suggest_edit",
        "add_clause",
        "next_clause",
        "finish_review"
    ] = Field(..., description="Type of action")

    clause_id: Optional[str] = Field(
        default=None,
        description="Clause being acted on"
    )

    content: Optional[str] = Field(
        default=None,
        description="Edit suggestion or clause text"
    )

    @model_validator(mode="after")
    def validate_fields(self):
        """Ensure required fields based on action_type."""

        # Actions that REQUIRE clause_id
        if self.action_type in ["flag_risk", "mark_safe", "suggest_edit"]:
            if not self.clause_id:
                raise ValueError(f"{self.action_type} requires clause_id")

        # Actions that REQUIRE content
        if self.action_type in ["suggest_edit", "add_clause"]:
            if not self.content:
                raise ValueError(f"{self.action_type} requires content")

        return self


# -------------------------------
# Observation Model
# -------------------------------
class LegalContractReviewObservation(Observation):
    """Observation representing current contract review state."""

    contract_id: str = Field(..., description="Unique contract ID")
    contract_type: str = Field(..., description="Type of contract (e.g., SaaS, NDA)")
    party_role: str = Field(..., description="Role of agent (client/vendor)")

    current_clause: Clause = Field(..., description="Current clause being reviewed")

    clause_index: int = Field(..., description="Current clause index")
    total_clauses: int = Field(..., description="Total number of clauses")

    issues_found: List[Dict] = Field(
        default_factory=list,
        description="List of issues identified so far"
    )

    time_step: int = Field(..., description="Current time step")

    reward: float = Field(default=0.0, description="Reward from last step")
    done: bool = Field(default=False, description="Whether episode is finished")