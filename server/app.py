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
    from legalcontractreview.models import (
        LegalContractReviewAction,
        LegalContractReviewObservation,
    )
    from legalcontractreview.server.environment import LegalcontractreviewEnvironment

    app = create_app(
        LegalcontractreviewEnvironment,
        LegalContractReviewAction,
        LegalContractReviewObservation,
        env_name="LegalContractReview",
        max_concurrent_envs=1,
    )

except Exception as e:
    import traceback
    print("🔥 CRITICAL: create_app failed")
    print(str(e))
    traceback.print_exc()

    # ✅ SAFE FALLBACK APP (PREVENTS CRASH)
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/")
    def root():
        return {"status": "fallback running"}

    @app.post("/reset")
    def reset():
        return {"error": "fallback"}

    @app.post("/step")
    def step():
        return {"error": "fallback"}


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
