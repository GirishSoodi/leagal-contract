# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
FastAPI application for the LegalContractReview Environment.
"""

# -------------------------
# Imports
# -------------------------
from openenv.core.env_server.http_server import create_app

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
# Health Check (IMPORTANT)
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Main entry
# -------------------------
def main():
    import uvicorn

    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=8000,
    )


# -------------------------
# CLI execution
# -------------------------
if __name__ == "__main__":
    main()

