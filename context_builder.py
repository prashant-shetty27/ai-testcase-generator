# context_builder.py


def _normalize(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def get_platform_context(platforms: list[str]) -> str:
    """
    Platform-aware context builder.
    Reflects real execution environment differences.
    """

    PLATFORM_ALIASES = {
        "androidapp": "android app",
        "iosapp": "ios app",
        "mobile web": "touch",
    }

    platform_map = {

        "web": [
            "Cross-browser compatibility (Chrome, Edge, Firefox, Safari)",
            "Responsive behavior across resolutions",
            "Keyboard navigation validation",
            "Browser back/forward behavior",
            "Cookie and cache handling impact",
            "Session persistence across tabs",
            "Accessibility (ARIA/basic WCAG checks)"
        ],

        "touch": [
            "Touch gesture validation (tap, scroll, swipe)",
            "Viewport responsiveness",
            "Mobile browser differences (Chrome/Safari)",
            "Network fluctuation handling",
            "Low bandwidth behavior",
            "Virtual keyboard interaction impact",
            "Orientation change handling"
        ],

        "android app": [
            "Activity lifecycle validation",
            "App background/foreground handling",
            "Push notification behavior",
            "Fragment navigation consistency",
            "Device fragmentation (OS versions)",
            "Crash recovery behavior",
            "Offline mode handling"
        ],

        "ios app": [
            "App lifecycle handling",
            "Push notification handling",
            "Gesture navigation consistency",
            "Background task management",
            "Device/OS version differences",
            "App permissions validation",
            "Crash recovery and resume validation"
        ],

        "hybrid app": [
            "WebView rendering consistency",
            "Native-to-web bridge validation",
            "JavaScript bridge stability",
            "Offline sync behavior",
            "Hybrid navigation flow consistency",
            "Cache and local storage sync issues",
            "App update compatibility"
        ],

        "api": [
            "Response time validation",
            "HTTP status code validation",
            "Schema validation",
            "Authentication token validation",
            "Invalid payload handling",
            "Rate limiting behavior",
            "Security validation",
            "Backward compatibility checks"
        ]
    }

    pointers = set()

    for p in platforms:
        if not p:
            continue

        normalized = _normalize(p)

        # Apply alias mapping
        normalized = PLATFORM_ALIASES.get(normalized, normalized)

        if normalized in platform_map:
            pointers.update(platform_map[normalized])

    return "\n".join(f"- {item}" for item in sorted(pointers))


def get_module_context(modules: list[str]) -> str:
    module_map = {
        "login": [
            "Valid and invalid credential validation",
            "Account lock after failed attempts",
            "Password policy enforcement",
            "CAPTCHA validation",
            "Session timeout behavior",
            "Concurrent login handling"
        ],
        "search": [
            "Empty search behavior",
            "Invalid input handling",
            "Filter combinations impact",
            "Sorting accuracy validation",
            "Pagination consistency",
            "Performance with large dataset"
        ],
        "booking": [
            "Inventory availability validation",
            "Price recalculation before confirmation",
            "GST calculation accuracy",
            "Duplicate booking prevention",
            "Refund and cancellation logic",
            "Booking confirmation generation"
        ],
        "payment": [
            "UPI validation",
            "Net banking flow validation",
            "Card validation (expired, CVV)",
            "Payment timeout handling",
            "Double charge prevention",
            "Transaction reconciliation"
        ]
    }

    pointers = set()

    for m in modules:
        if not m:
            continue

        normalized = _normalize(m)

        if normalized in module_map:
            pointers.update(module_map[normalized])

    return "\n".join(f"- {item}" for item in sorted(pointers))


def get_page_context(pages: list[str]) -> str:
    page_map = {
        "result page": [
            "Result count accuracy",
            "Filter impact on results",
            "Sorting reflection in UI",
            "Price consistency",
            "Pagination control validation",
            "No result messaging"
        ],
        "details page": [
            "Listing vs details data consistency",
            "Room availability accuracy",
            "Price breakdown (base + GST)",
            "Amenities accuracy",
            "Cancellation policy display",
            "Back navigation consistency"
        ],
        "checkout page": [
            "Guest information validation",
            "Coupon code validation",
            "Price recalculation before payment",
            "Tax recalculation",
            "Payment method selection logic",
            "Booking summary accuracy"
        ]
    }

    pointers = set()

    for page in pages:
        if not page:
            continue

        normalized = _normalize(page)

        if normalized in page_map:
            pointers.update(page_map[normalized])

    return "\n".join(f"- {item}" for item in sorted(pointers))


def build_context_block(platforms, modules, pages, classification=None):
    """
    Context builder only.
    No classification logic inside.
    Optionally classification-aware for scope emphasis.
    """

    platform_context = get_platform_context(platforms)
    module_context = get_module_context(modules)
    page_context = get_page_context(pages)

    classification_context = ""

    if classification:
        classified_type = classification.get("type", "unknown")

        if classified_type == "performance":
            classification_context += """
Additional Performance Focus:
- Load variation scenarios
- Stress and endurance checks
- Concurrency conflicts
"""

        elif classified_type == "security":
            classification_context += """
Additional Security Focus:
- Data exposure risks
- Privilege escalation scenarios
- Session hijacking checks
"""

        elif classified_type == "api":
            classification_context += """
Additional API Focus:
- Contract validation
- Backward compatibility
- Versioning risks
"""

    return f"""
Platform-Specific Considerations:
{platform_context}

Module-Specific Considerations:
{module_context}

Page-Specific Considerations:
{page_context}

{classification_context}
"""