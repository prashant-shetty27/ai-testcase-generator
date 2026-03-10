class ManualTemplate:

    @staticmethod
    def map_testcase(category, tc):

        steps = tc.get("steps", [])

        if not steps:
            steps_text = ""
        elif len(steps) == 1:
            steps_text = steps[0]
        else:
            steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

        return [
            tc.get("testcase_id"),
            tc.get("priority", "Medium"),
            category,
            tc.get("scenario") or tc.get("title") or "N/A",
            steps_text,
            tc.get("examples", ""),
            tc.get("expected_result", "")
        ]