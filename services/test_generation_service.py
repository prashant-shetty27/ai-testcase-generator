from requirement_analyzer import analyze_requirement
from testcase_generator import generate_testcases
from engines.boundary_engine import generate_boundary_tests
from engines.parameter_engine import generate_parameter_tests
from engines.platform_engine import generate_platform_checks
from engines.dedup_engine import deduplicate_full_suite
from engines.risk_engine import apply_risk_to_tests

def generate_full_test_suite(requirement):

    analysis = analyze_requirement(requirement)

    analysis["platforms"] = [
        "web",
        "mobile_web",
        "android_app",
        "ios_app"
    ]

    tests = generate_testcases(analysis)

    if not isinstance(tests, dict):
       raise ValueError("AI returned invalid test structure")

    # platform tests
    tests.setdefault("platform_tests", [])
    tests["platform_tests"].extend(
        generate_platform_checks(
            analysis.get("feature", "Feature"),
            analysis["platforms"]
    )
)

    # parameter negatives
    tests.setdefault("negative_tests", [])
    tests["negative_tests"].extend(generate_parameter_tests(analysis))

    # boundary tests
    tests.setdefault("boundary_value_tests", [])
    tests["boundary_value_tests"].extend(generate_boundary_tests(analysis))


    # ✅ Remove duplicates across engines
    tests = deduplicate_full_suite(tests)

    # ✅ Apply risk levels to tests
    tests = apply_risk_to_tests(tests)

    return tests