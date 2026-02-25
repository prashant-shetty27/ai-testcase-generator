import re


def generate_boundary_tests(analysis):

    boundary_tests = []

    constraints = analysis.get("constraints", [])

    for rule in constraints:

        # ---- TIME BASED RULES ----
        time_match = re.search(r"(\d+)\s*minute", rule.lower())
        if time_match:
            minutes = int(time_match.group(1))

            boundary_tests.extend([
                {
                    "testcase_id": f"AUTO_BVA_TIME_1",
                    "scenario": f"OTP used just before expiry ({minutes-1}m59s)",
                    "steps": [
                        "Request OTP",
                        f"Wait {minutes-1} minutes 59 seconds",
                        "Submit OTP"
                    ],
                    "expected_result": "OTP accepted"
                },
                {
                    "testcase_id": f"AUTO_BVA_TIME_2",
                    "scenario": f"OTP used exactly at expiry ({minutes} minutes)",
                    "steps": [
                        "Request OTP",
                        f"Wait exactly {minutes} minutes",
                        "Submit OTP"
                    ],
                    "expected_result": "System behavior matches expiry boundary rule"
                },
                {
                    "testcase_id": f"AUTO_BVA_TIME_3",
                    "scenario": f"OTP used after expiry ({minutes+1} minutes)",
                    "steps": [
                        "Request OTP",
                        f"Wait {minutes+1} minutes",
                        "Submit OTP"
                    ],
                    "expected_result": "OTP rejected as expired"
                }
            ])

        # ---- COUNT LIMIT RULES ----
        count_match = re.search(r"(\d+)\s*(attempt|try)", rule.lower())
        if count_match:
            limit = int(count_match.group(1))

            boundary_tests.extend([
                {
                    "testcase_id": "AUTO_BVA_COUNT_1",
                    "scenario": f"OTP correct at final allowed attempt ({limit})",
                    "steps": [
                        f"Enter incorrect OTP {limit-1} times",
                        "Enter correct OTP"
                    ],
                    "expected_result": "Password reset allowed"
                },
                {
                    "testcase_id": "AUTO_BVA_COUNT_2",
                    "scenario": f"OTP entered beyond allowed attempts ({limit+1})",
                    "steps": [
                        f"Enter incorrect OTP {limit} times",
                        "Attempt OTP again"
                    ],
                    "expected_result": "User blocked; reset required"
                }
            ])

    return boundary_tests