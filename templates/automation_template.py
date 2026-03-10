class AutomationTemplate:

    @staticmethod
    def map_testcase(category, tc):
        steps = tc.get("steps", [])

        # Format steps
        if not steps:
            steps_text = ""
        elif len(steps) == 1:
            steps_text = steps[0]
        else:
            steps_text = "\n".join(
                [f"{i+1}. {step}" for i, step in enumerate(steps)]
            )

        return [
            tc.get("testcase_id"),
            "High",  # or tc.get("priority", "High") if AI provides it
            category,
            tc.get("scenario"),
            steps_text,
            tc.get("expected_result"),
            tc.get("examples", "")
        ]