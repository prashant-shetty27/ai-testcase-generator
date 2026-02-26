def generate_platform_checks(feature, platforms):

    checks = []
    counter = 1

    def create_test(description):
        nonlocal counter
        tc = {
            "testcase_id": f"PLT_{counter:03}",
            "scenario": description,
            "steps": [
                f"Open application feature: {feature}",
                "Execute workflow on specified platform"
            ],
            "expected_result": f"{feature} works correctly without UI or functional issues"
        }
        counter += 1
        return tc

    if "web" in platforms:
        checks.extend([
            create_test(f"{feature} works on Chrome browser"),
            create_test(f"{feature} works on Firefox browser"),
            create_test(f"{feature} responsive layout on desktop resolutions"),
            create_test(f"{feature} supported on iPad/tablet view"),
        ])

    if "mobile_web" in platforms:
        checks.extend([
            create_test(f"{feature} works on mobile Safari"),
            create_test(f"{feature} works on Android Chrome browser"),
            create_test(f"{feature} works on low screen resolutions (320px–480px)"),
            create_test(f"{feature} keyboard does not hide OTP fields"),
        ])

    if "android_app" in platforms:
        checks.extend([
            create_test(f"{feature} works on latest Android version"),
            create_test(f"{feature} works on commonly used Android versions"),
            create_test(f"{feature} handles background/foreground switching"),
            create_test(f"{feature} OTP autofill behavior on Android"),
        ])

    if "ios_app" in platforms:
        checks.extend([
            create_test(f"{feature} works on latest iOS version"),
            create_test(f"{feature} works on commonly used iOS versions"),
            create_test(f"{feature} OTP autofill from SMS"),
            create_test(f"{feature} behavior with iOS keyboard and permissions"),
        ])

    return checks
