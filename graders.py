try:
    from openenv.core.env_server.interfaces import Grader
except ImportError:
    # Fallback for environments where openenv-core is not installed
    class Grader:
        def grade(self, state, env):
            raise NotImplementedError

class LegalContractGrader(Grader):
    def grade(self, state, env):
        try:
            # The environment should have a compute_score method
            return float(env.compute_score())
        except Exception as e:
            print(f"Grader error: {e}")
            return 0.0


easy_grader = LegalContractGrader()
medium_grader = LegalContractGrader()
hard_grader = LegalContractGrader()

