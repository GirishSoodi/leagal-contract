# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the LegalContractReview Environment.
"""

# -------------------------
# Imports
# -------------------------

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required. Install dependencies using:\n    uv sync\n"
    ) from e

from legalcontractreview.models import (
    LegalContractReviewAction,
    LegalContractReviewObservation,
)

from legalcontractreview.server.environment import LegalcontractreviewEnvironment


# -------------------------
# Create FastAPI app
# -------------------------

app = create_app(
    LegalcontractreviewEnvironment,
    LegalContractReviewAction,
    LegalContractReviewObservation,
    env_name="LegalContractReview",
    max_concurrent_envs=1,
)


# -------------------------
# Main entry (REQUIRED)
# -------------------------

def main():
    import uvicorn

    uvicorn.run(
        "legalcontractreview.server.app:app",
        host="0.0.0.0",
        port=8000,
    )


# -------------------------
# CLI execution (REQUIRED)
# -------------------------

if __name__ == "__main__":
    main()

