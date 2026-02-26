class ManualTemplate:

    @staticmethod
    def map_testcase(category, tc):
        steps = tc.get("steps", [])

        # Format steps: number only if more than 1 step
        if not steps:
            steps_text = ""
        elif len(steps) == 1:
            steps_text = steps[0]
        else:
            steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

        return [
            tc.get("testcase_id"),
            category,
            tc.get("scenario"),
            steps_text,
            tc.get("expected_result")
        ]