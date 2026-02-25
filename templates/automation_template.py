def get_headers():
    return [
        "Test ID",
        "Test Name",
        "Preconditions",
        "Test Steps",
        "Assertions",
        "Automation Candidate",
        "Priority"
    ]


def map_testcase(category, tc):
    return [
        tc.get("testcase_id"),
        tc.get("scenario"),
        "User exists and system available",
        "\n".join(
    [f"{i+1}. {step}" for i, step in enumerate(tc.get("steps", []))]
),
        tc.get("expected_result"),
        "Yes" if category == "automation_candidates" else "No",
        "High"
    ]