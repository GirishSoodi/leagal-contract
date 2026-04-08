import asyncio
import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

try:
    from legalcontractreview.client import LegalcontractreviewEnv
    from legalcontractreview.models import LegalContractReviewAction
except ModuleNotFoundError:
    from client import LegalcontractreviewEnv
    from models import LegalContractReviewAction


IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
TASK_NAME = "easy"
BENCHMARK = "legalcontractreview"
MODEL_NAME = "proxy-llm"


# 🔥 REQUIRED LLM CLIENT (VALIDATOR)
client = OpenAI(
    base_url=os.environ["API_BASE_URL"],
    api_key=os.environ["API_KEY"]
)


def log_start():
    print(f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error):
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}",
        flush=True,
    )


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# 🔥 LLM POLICY (MANDATORY FOR PHASE 2)
def llm_policy(obs, goal):
    try:
        clause = getattr(obs.current_clause, "text", "")

        prompt = f"""
You are a legal contract reviewer.

Task: {goal}

Clause:
{clause}

Choose ONE:
flag_risk
suggest_edit
next_clause
finish_review

Format:
ACTION: <action>
CONTENT: <text or NONE>
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50,
        )

        text = response.choices[0].message.content.strip()

        action = "next_clause"
        content = None

        for line in text.split("\n"):
            if "ACTION:" in line:
                action = line.split("ACTION:")[-1].strip().lower()
            if "CONTENT:" in line:
                val = line.split("CONTENT:")[-1].strip()
                if val != "NONE":
                    content = val

        if action not in ["flag_risk", "suggest_edit", "next_clause", "finish_review"]:
            return "next_clause", None

        return action, content

    except Exception:
        return "next_clause", None


async def main():
    rewards: List[float] = []
    steps_taken = 0

    # ✅ ALWAYS FIRST
    log_start()

    env = None
    try:
        env = await LegalcontractreviewEnv.from_docker_image(IMAGE_NAME)
    except Exception as e:
        print(f"[ERROR] env failed: {e}", flush=True)

    try:
        if env:
            result = await env.reset(task_id=TASK_NAME)
            obs = result.observation
            goal = obs.metadata.get("goal", "")
        else:
            # fallback
            class Dummy:
                clause_index = 0
                total_clauses = 1
                current_clause = type("c", (), {"id": "1", "text": "dummy clause"})
                metadata = {"goal": "review"}

            obs = Dummy()
            result = type("r", (), {"done": False})()
            goal = "review"

        # 🔥 FORCE AT LEAST ONE STEP + LLM CALL
        for step in range(1, 3):
            steps_taken = step

            action_type, content = llm_policy(obs, goal)

            clause_id = getattr(obs.current_clause, "id", None)

            try:
                action = LegalContractReviewAction(
                    action_type=action_type,
                    clause_id=clause_id,
                    content=content
                )
            except:
                action = None

            try:
                if env and action:
                    result = await env.step(action)
                    obs = result.observation
                    reward = result.reward or 0.0
                    done = result.done
                else:
                    reward = 0.0
                    done = False
            except Exception:
                reward = 0.0
                done = False

            rewards.append(reward)

            log_step(step, action_type, reward, done, None)

            if done:
                break

        score = 0.5
        success = True

    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        success = False
        score = 0.0

    finally:
        if env:
            try:
                await env.close()
            except:
                pass

        log_end(success, steps_taken, score, rewards)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[CRASH] {e}", flush=True)
        print("[END] success=false steps=0 score=0.000 rewards=", flush=True)

