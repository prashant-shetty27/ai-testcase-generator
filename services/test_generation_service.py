from requirement_analyzer import analyze_requirement
from testcase_generator import generate_testcases
from engines.boundary_engine import generate_boundary_tests
from engines.parameter_engine import generate_parameter_tests
from engines.platform_engine import generate_platform_checks

def generate_full_test_suite(request):

    analysis = analyze_requirement(request.requirement)
    analysis["platforms"] = request.platforms

    tests = generate_testcases(analysis)

    # Platform tests
    if request.include_platform_tests:
        tests["platform_tests"] = generate_platform_checks(
            analysis["feature"],
            analysis["platforms"]
        )

    # Parameter negative tests
    if request.include_parameter_tests:
        tests.setdefault("negative_tests", [])
        tests["negative_tests"].extend(generate_parameter_tests(analysis))

    # Boundary tests
    if request.include_boundary_tests:
        tests.setdefault("boundary_value_tests", [])
        tests["boundary_value_tests"].extend(generate_boundary_tests(analysis))

    return tests