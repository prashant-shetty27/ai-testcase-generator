HIGH_RISK_KEYWORDS = [
    "login",
    "password",
    "otp",
    "authentication",
    "payment",
    "transaction",
    "reset",
    "security",
    "account",
]

MEDIUM_RISK_KEYWORDS = [
    "update",
    "edit",
    "submit",
    "verification",
    "api",
    "network",
]

LOW_RISK_KEYWORDS = [
    "ui",
    "layout",
    "responsive",
    "display",
    "cosmetic",
]


def calculate_risk_level(text: str) -> str:
    """
    Decide risk level based on scenario keywords.
    """

    if not text:
        return "MEDIUM"

    text_lower = text.lower()

    for word in HIGH_RISK_KEYWORDS:
        if word in text_lower:
            return "HIGH"

    for word in MEDIUM_RISK_KEYWORDS:
        if word in text_lower:
            return "MEDIUM"

    return "LOW"


def apply_risk_to_tests(tests: dict):
    """
    Add risk priority to every testcase.
    """

    for category, test_list in tests.items():

        if not isinstance(test_list, list):
            continue

        for test in test_list:

            # platform tests are strings
            if isinstance(test, str):
                continue

            scenario = test.get("scenario", "")
            test["risk"] = calculate_risk_level(scenario)

    return tests