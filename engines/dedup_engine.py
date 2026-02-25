def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    Removes casing and extra spaces.
    """
    if not text:
        return ""

    return " ".join(text.lower().strip().split())


def deduplicate_testcases(test_list):
    """
    Removes duplicate testcases based on scenario similarity.
    """

    seen = set()
    unique_tests = []

    for test in test_list:

        # Works for both dict tests and string platform checks
        if isinstance(test, dict):
            key = normalize_text(test.get("scenario", ""))
        else:
            key = normalize_text(str(test))

        if key not in seen:
            seen.add(key)
            unique_tests.append(test)

    return unique_tests


def deduplicate_full_suite(tests: dict):
    """
    Deduplicate all testcase categories safely.
    """

    categories = [
        "positive_tests",
        "negative_tests",
        "edge_cases",
        "boundary_value_tests",
        "api_tests",
        "network_tests",
        "automation_candidates",
        "platform_tests",
    ]

    for category in categories:
        if category in tests:
            tests[category] = deduplicate_testcases(tests[category])

    return tests