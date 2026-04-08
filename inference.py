import asyncio
import os
import sys
from typing import List

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# SAFE IMPORTS
# =========================================================
try:
    from legalcontractreview.client import LegalcontractreviewEnv
    from legalcontractreview.models import LegalContractReviewAction
except ModuleNotFoundError:
    from client import LegalcontractreviewEnv
    from models import LegalContractReviewAction


# =========================================================
# CONFIG (SAFE DEFAULTS)
# =========================================================
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "meta-llama/Meta-Llama-3-8B-Instruct"
API_KEY = os.getenv("HF_TOKEN")

MAX_STEPS = 50


# =========================================================
# SAFE LLM POLICY (NO CRASH GUARANTEED)
# =========================================================
def llm_policy(obs, goal, client):
    try:
        clause = obs.current_clause

        prompt = f"""
You are a legal contract auditor.

Your task: {goal}

Clause:
\"\"\"
{clause.text}
\"\"\"

Allowed actions:
- flag_risk
- suggest_edit
- next_clause
- finish_review

STRICT RULES:
1. Use flag_risk ONLY if clearly HIGH risk
2. Use suggest_edit ONLY if clause is incorrect or incomplete
3. Otherwise use next_clause
4. DO NOT repeat same action unnecessarily
5. Be conservative — wrong actions are penalized heavily

Output EXACTLY in this format:
ACTION: <one of the actions>
CONTENT: <text or NONE>
"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100,
        )

        text = response.choices[0].message.content.strip()

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
# MAIN TASK LOOP (FIXED ENV INIT)
# =========================================================
async def run_task(task_id: str):
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = None

    # =====================================================
    # 🔥 FIX: REMOVE DOCKER, USE VALIDATOR ENV
    # =====================================================
    try:
        base_url = os.getenv("ENV_BASE_URL", "http://localhost:8000")
        print(f"[INFO] Connecting to env at {base_url}")

        env = LegalcontractreviewEnv(base_url=base_url)

    except Exception as e:
        print(f"[ERROR] Env init failed: {e}")
        return

    rewards: List[float] = []
    steps_taken = 0

    try:
        print(f"[START] task={task_id} env=legalcontractreview model={MODEL_NAME}")

        try:
            result = await env.reset(task_id=task_id)
        except Exception as e:
            print(f"[ERROR] Reset failed: {e}")
            return

        obs = result.observation
        goal = obs.metadata.get("goal", "")

        last_action = None

        for step in range(1, MAX_STEPS + 1):

            if getattr(result, "done", False):
                break

            steps_taken = step

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
                current_clause_id = obs.current_clause.id
            except Exception:
                current_clause_id = None

            if action_type in ["flag_risk", "suggest_edit"]:
                clause_id = current_clause_id
            else:
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
                error = "null"
            except Exception as e:
                reward = 0.0
                error = str(e).replace("\n", " ")
                result = type("obj", (), {"done": False})()

            rewards.append(reward)

            print(
                f"[STEP] step={step} action={action_type} "
                f"reward={reward:.2f} done={str(getattr(result, 'done', False)).lower()} "
                f"error={error}"
            )

            if getattr(result, "done", False):
                break

        final_score = getattr(obs, "metadata", {}).get("score", 0.0)
        success = final_score > 0.7

        rewards_str = ",".join(f"{r:.2f}" for r in rewards)

        print(
            f"[END] success={str(success).lower()} "
            f"steps={steps_taken} score={final_score:.2f} rewards={rewards_str}"
        )

    except Exception as e:
        print(f"[FATAL ERROR] {e}", file=sys.stderr)
        print(f"[END] success=false steps={steps_taken} score=0.00 rewards=0.00")

    finally:
        try:
            if env:
                await env.close()
        except Exception:
            pass


# =========================================================
# ENTRY POINT
# =========================================================
async def main():
    for tid in ["easy", "medium", "hard"]:
        try:
            await run_task(tid)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[TASK ERROR] {tid}: {e}")


if __name__ == "__main__":
    if not API_KEY:
        print("[WARNING] Missing API key — running in fallback mode")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[CRASH] {e}")

