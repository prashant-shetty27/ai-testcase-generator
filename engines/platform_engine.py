def generate_platform_checks(feature, platforms):

    checks = []

    if "web" in platforms:
        checks.extend([
            f"{feature} works on Chrome, Firefox, Edge",
            f"{feature} responsive layout on desktop resolutions",
            f"{feature} supported on iPad/tablet view"
        ])

    if "mobile_web" in platforms:
        checks.extend([
            f"{feature} works on mobile Safari",
            f"{feature} works on Chrome Android browser",
            f"{feature} works on low screen resolutions (320px–480px)",
            f"{feature} keyboard does not hide OTP fields"
        ])

    if "android_app" in platforms:
        checks.extend([
            f"{feature} works on latest Android version",
            f"{feature} works on most-used Android versions",
            f"{feature} handles app background/foreground switching",
            f"{feature} OTP autofill behavior on Android"
        ])

    if "ios_app" in platforms:
        checks.extend([
            f"{feature} works on latest iOS version",
            f"{feature} works on commonly used iOS versions",
            f"{feature} OTP autofill from SMS",
            f"{feature} behavior with iOS keyboard and permissions"
        ])

    return checks
