# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""LegalContractReview Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import LegalContractReviewAction, LegalContractReviewObservation


class LegalcontractreviewEnv(
    EnvClient[
        LegalContractReviewAction,
        LegalContractReviewObservation,
        State
    ]
):
    """
    Client for the LegalContractReview Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions.

    Example:
        >>> with LegalcontractreviewEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.current_clause)
        ...
        ...     action = LegalContractReviewAction(
        ...         action_type="flag_risk",
        ...         clause_id="c2"
        ...     )
        ...     result = client.step(action)
        ...     print(result.observation.issues_found)
    """

    def _step_payload(self, action: LegalContractReviewAction) -> Dict:
        """
        Convert LegalContractReviewAction to JSON payload.

        Args:
            action: LegalContractReviewAction instance

        Returns:
            JSON-ready dictionary
        """
        return {
            "action_type": action.action_type,
            "clause_id": action.clause_id,
            "content": action.content,
        }

    def _parse_result(
        self,
        payload: Dict
    ) -> StepResult[LegalContractReviewObservation]:
        """
        Parse server response into StepResult.

        Args:
            payload: JSON response from server

        Returns:
            StepResult with LegalContractReviewObservation
        """

        obs_data = payload.get("observation", {})

        observation = LegalContractReviewObservation(
            contract_id=obs_data.get("contract_id"),
            contract_type=obs_data.get("contract_type"),
            party_role=obs_data.get("party_role"),

            current_clause=obs_data.get("current_clause", {}),
            clause_index=obs_data.get("clause_index", 0),
            total_clauses=obs_data.get("total_clauses", 0),

            issues_found=obs_data.get("issues_found", []),
            time_step=obs_data.get("time_step", 0),

            reward=payload.get("reward"),
            done=payload.get("done", False),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from /state

        Returns:
            State object
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )