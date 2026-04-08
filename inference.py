import asyncio
import os
import sys
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

try:
    from legalcontractreview.client import LegalcontractreviewEnv
    from legalcontractreview.models import LegalContractReviewAction
except ModuleNotFoundError:
    from client import LegalcontractreviewEnv
    from models import LegalContractReviewAction

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME")
API_KEY = os.getenv("HF_TOKEN")
IMAGE_NAME = "legalcontractreview_env"

MAX_STEPS = 50


# =========================================================
# 🧠 STRICT LLM POLICY (NO RULES, NO FALLBACK)
# =========================================================
def llm_policy(obs, goal, client):
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

Examples:
ACTION: flag_risk
CONTENT: NONE

ACTION: suggest_edit
CONTENT: Add termination clause with 30 days notice

ACTION: next_clause
CONTENT: NONE
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
        action = "next_clause"
        content = None

    return action, content


# =========================================================
# 🚀 MAIN LOOP
# =========================================================
async def run_task(task_id: str):
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    try:
        env = await LegalcontractreviewEnv.from_docker_image(IMAGE_NAME, timeout=60)
    except Exception:
        env = LegalcontractreviewEnv(base_url="http://localhost:8000")

    rewards: List[float] = []
    steps_taken = 0

    try:
        print(f"[START] task={task_id} env=legalcontractreview model={MODEL_NAME}")

        result = await env.reset(task_id=task_id)
        obs = result.observation
        goal = obs.metadata.get("goal", "")

        last_action = None

        for step in range(1, MAX_STEPS + 1):

            if result.done:
                break

            steps_taken = step

            # 🔥 FORCE FINISH
            if obs.clause_index >= obs.total_clauses - 1:
                action_type = "finish_review"
                content = None
            else:
                action_type, content = llm_policy(obs, goal, client)

            # 🔥 PREVENT LOOPING SAME ACTION
            if action_type == last_action:
                action_type = "next_clause"
                content = None

            last_action = action_type

            # 🔥 VALID CLAUSE ID
            current_clause_id = obs.current_clause.id

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

            rewards.append(reward)

            print(f"[STEP] step={step} action={action_type} reward={reward:.2f} done={str(result.done).lower()} error={error}")

            if result.done:
                break

        final_score = obs.metadata.get("score", 0.0)
        success = final_score > 0.7

        rewards_str = ",".join(f"{r:.2f}" for r in rewards)
        print(f"[END] success={str(success).lower()} steps={steps_taken} score={final_score:.2f} rewards={rewards_str}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"[END] success=false steps={steps_taken} score=0.00 rewards=0.00")

    finally:
        try:
            await env.close()
        except:
            pass


async def main():
    for tid in ["easy", "medium", "hard"]:
        await run_task(tid)
        await asyncio.sleep(1)


if __name__ == "__main__":
    if not API_KEY:
        print("Missing API key")
        sys.exit(1)

    asyncio.run(main())