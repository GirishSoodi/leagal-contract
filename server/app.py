from openenv.core.env_server.http_server import create_app

from models import (
    LegalContractReviewAction,
    LegalContractReviewObservation,
)

from server.environment import LegalcontractreviewEnvironment


app = create_app(
    LegalcontractreviewEnvironment,
    LegalContractReviewAction,
    LegalContractReviewObservation,
    env_name="LegalContractReview",
    max_concurrent_envs=1,
)


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()