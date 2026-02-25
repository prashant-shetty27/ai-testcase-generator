import re


def detect_parameter_type(input_text):

    text = input_text.lower()

    if "email" in text:
        return "email"

    if "phone" in text or "mobile" in text:
        return "phone"

    if "otp" in text:
        return "otp"

    if "password" in text:
        return "password"

    return "generic"


def generate_parameter_tests(analysis):

    parameter_tests = []

    inputs = analysis.get("inputs", [])

    for inp in inputs:

        param_type = detect_parameter_type(inp)

        # ---- EMAIL TESTS ----
        if param_type == "email":
            parameter_tests.extend([
                {
                    "testcase_id": "AUTO_PARAM_EMAIL_1",
                    "scenario": "Invalid email format (missing @)",
                    "steps": ["Enter email 'userexample.com'"],
                    "expected_result": "Validation error displayed"
                },
                {
                    "testcase_id": "AUTO_PARAM_EMAIL_2",
                    "scenario": "Empty email field",
                    "steps": ["Leave email blank and submit"],
                    "expected_result": "Required field validation shown"
                }
            ])

        # ---- OTP TESTS ----
        elif param_type == "otp":
            parameter_tests.extend([
                {
                    "testcase_id": "AUTO_PARAM_OTP_1",
                    "scenario": "OTP with alphabets",
                    "steps": ["Enter OTP '12AB34'"],
                    "expected_result": "OTP rejected"
                },
                {
                    "testcase_id": "AUTO_PARAM_OTP_2",
                    "scenario": "OTP shorter than expected length",
                    "steps": ["Enter OTP '123'"],
                    "expected_result": "Validation error displayed"
                }
            ])

        # ---- PASSWORD TESTS ----
        elif param_type == "password":
            parameter_tests.extend([
                {
                    "testcase_id": "AUTO_PARAM_PASS_1",
                    "scenario": "Weak password",
                    "steps": ["Enter password '12345'"],
                    "expected_result": "Password strength validation error"
                },
                {
                    "testcase_id": "AUTO_PARAM_PASS_2",
                    "scenario": "Very long password input",
                    "steps": ["Enter password with 256 characters"],
                    "expected_result": "System handles max length safely"
                }
            ])

        # ---- PHONE TESTS ----
        elif param_type == "phone":
            parameter_tests.extend([
                {
                    "testcase_id": "AUTO_PARAM_PHONE_1",
                    "scenario": "Phone number with letters",
                    "steps": ["Enter phone '98AB12345'"],
                    "expected_result": "Validation error"
                },
                {
                    "testcase_id": "AUTO_PARAM_PHONE_2",
                    "scenario": "Phone number too short",
                    "steps": ["Enter phone '12345'"],
                    "expected_result": "Invalid phone number message"
                }
            ])

    return parameter_tests