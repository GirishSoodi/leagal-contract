# from openenv.core.env_server.interfaces import Grader # Removed base class as it causes import errors

class LegalContractGrader:
    def grade(self, state, env):
        try:
            return float(env.compute_score())
        except Exception:
            return 0.0


easy_grader = LegalContractGrader()
medium_grader = LegalContractGrader()
hard_grader = LegalContractGrader()

