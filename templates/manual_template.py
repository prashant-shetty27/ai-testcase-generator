def get_headers():
    return [
        "TestCase ID",
        "Scenario",
        "Steps",
        "Expected Result",
        "Type",
        "Status",
        "Comments"
    ]


def map_testcase(category, tc):
    return [
        tc.get("testcase_id"),
        tc.get("scenario"),
        "\n".join(
    [f"{i+1}. {step}" for i, step in enumerate(tc.get("steps", []))]
),
        tc.get("expected_result"),
        category,
        "Draft",
        ""
    ]