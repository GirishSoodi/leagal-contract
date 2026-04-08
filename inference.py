import asyncio
import os
from typing import List, Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# IMPORT ENV
# =========================================================
try:
    from legalcontractreview.client import LegalcontractreviewEnv
    from legalcontractreview.models import LegalContractReviewAction
except ModuleNotFoundError:
    from client import LegalcontractreviewEnv
    from models import LegalContractReviewAction


# =========================================================
# CONFIG (STRICT TEMPLATE)
# =========================================================
IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")  # REQUIRED
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")

TASK_NAME = os.getenv("TASK_NAME", "easy")
BENCHMARK = os.getenv("BENCHMARK", "legalcontractreview")

MAX_STEPS = 50
TEMPERATURE = 0.0
MAX_TOKENS = 120


# =========================================================
# LOGGING (STRICT FORMAT)
# =========================================================
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# =========================================================
# LLM POLICY
# =========================================================
def llm_policy(obs, goal, client):
    try:
        clause = obs.current_clause

        prompt = f"""
You are a legal contract auditor.

Task: {goal}

Clause:
\"\"\"
{clause.text}
\"\"\"

Actions:
flag_risk
suggest_edit
next_clause
finish_review

Output EXACT:
ACTION: <action>
CONTENT: <text or NONE>
"""

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        text = (completion.choices[0].message.content or "").strip()

        action = "next_clause"
        content = None

        for line in text.split("\n"):
            if line.startswith("ACTION:"):
                action = line.replace("ACTION:", "").strip().lower()
            if line.startswith("CONTENT:"):
                val = line.replace("CONTENT:", "").strip()
                if val != "NONE":
                    content = val

        if action not in ["flag_risk", "suggest_edit", "next_clause", "finish_review"]:
            return "next_clause", None

        return action, content

    except Exception:
        return "next_clause", None


# =========================================================
# MAIN (FINAL FIXED VERSION)
# =========================================================
async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"🔄 Starting docker environment: {IMAGE_NAME}", flush=True)

    # ✅ ONLY VALID METHOD
    env = await LegalcontractreviewEnv.from_docker_image(IMAGE_NAME)

    rewards: List[float] = []
    steps_taken = 0
    success = False
    score = 0.0

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task_id=TASK_NAME)
        obs = result.observation
        goal = obs.metadata.get("goal", "")

        last_action = None

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            try:
                if obs.clause_index >= obs.total_clauses - 1:
                    action_type = "finish_review"
                    content = None
                else:
                    action_type, content = llm_policy(obs, goal, client)
            except Exception:
                action_type, content = "next_clause", None

            if action_type == last_action:
                action_type = "next_clause"
                content = None

            last_action = action_type

            try:
                clause_id = obs.current_clause.id if action_type in ["flag_risk", "suggest_edit"] else None
            except Exception:
                clause_id = None

            action = LegalContractReviewAction(
                action_type=action_type,
                clause_id=clause_id,
                content=content
            )

            try:
                result = await env.step(action)
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done
                error = None
            except Exception as e:
                reward = 0.0
                done = False
                error = str(e)
                result = type("obj", (), {"done": False})()

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_type, reward=reward, done=done, error=error)

            if done:
                break

        score = getattr(obs, "metadata", {}).get("score", 0.0)
        success = score > 0.7

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)

        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())

