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
            "Browsers: Chrome 120+, Firefox 120+, Edge 120+, Safari 16+, Opera — each must be tested separately",
            "Resolutions: 1366x768 (most common), 1920x1080 (FHD), 1440x900, 1280x800, 2560x1440 (QHD)",
            "Zoom levels: 75%, 100%, 125%, 150% — layout must not break at non-default zoom",
            "OS: Windows 10, Windows 11, macOS Ventura/Sonoma, Ubuntu — test on at least 2 OS types",
            "Keyboard navigation: Tab, Enter, Escape, arrow keys must all work correctly",
            "Browser back/forward button behavior — state must not break on navigation",
            "Cookie and cache: test with cleared cache, expired session, third-party cookie restrictions",
            "Session persistence across tabs — same session, different tab should not cause conflict",
            "Accessibility: ARIA labels, WCAG contrast ratios, screen reader compatibility",
            "Incognito / private browsing mode behavior"
        ],

        "touch": [
            "Mobile browsers: Chrome for Android, Safari for iOS, Samsung Internet, Firefox Mobile, UC Browser",
            "Screen sizes: 4-inch (SE), 5.4-inch, 6.1-inch, 6.7-inch (Plus/Max) — test each layout breakpoint",
            "Gestures: tap, long-press, swipe, pinch-to-zoom, double-tap — must all be validated",
            "Orientation: portrait and landscape — UI must reflow correctly",
            "Virtual keyboard: input fields must scroll above keyboard; no content hidden behind it",
            "Network conditions: 4G, 3G, 2G, offline — test graceful degradation",
            "Viewport meta tag behavior — no horizontal scroll on mobile",
            "iOS Safari vs Android Chrome rendering differences — test separately"
        ],

        "android app": [
            "OS versions: Android 8 (Oreo), 9 (Pie), 10, 11, 12, 13, 14 — test minimum 3 versions",
            "Device brands: Samsung Galaxy (S/A/M series), Xiaomi Redmi/Note, OnePlus, POCO, Realme, Motorola, Vivo, Oppo",
            "Screen resolutions: HD 720p, FHD 1080p, FHD+ 1080x2400, QHD 1440p — test on at least 2",
            "Chipsets: Snapdragon (high-end), MediaTek Helio/Dimensity (mid-range), Exynos (Samsung) — behaviour may differ",
            "RAM variants: 2GB, 3GB, 4GB, 6GB — test on low-RAM (2-3GB) for memory pressure",
            "Navigation: gesture navigation (Android 10+) vs 3-button nav bar — both must work",
            "Permissions dialogs: runtime permissions (camera, storage, location) — grant and deny both",
            "Activity lifecycle: background→foreground, app kill→relaunch, split screen, picture-in-picture",
            "Push notifications: FCM delivery, tap-to-open, notification tray handling",
            "Crash recovery: app must restore state after unexpected kill",
            "Offline mode: graceful degradation, cached data display, reconnect sync",
            "Dark mode (Android 10+): UI must render correctly in both light and dark system themes",
            "Font scaling: system accessibility font size at 85%, 100%, 130%, 200%"
        ],

        "ios app": [
            "iOS versions: iOS 15, iOS 16, iOS 17, iOS 18 — test minimum 3 versions",
            "Devices: iPhone SE (small/home button), iPhone 12/13 (notch), iPhone 14 Pro/15 Pro (Dynamic Island), iPhone Plus/Max (large)",
            "iPad: if app supports iPad — test split view, slide over, stage manager",
            "Screen sizes: 4.7-inch (SE), 5.4-inch (mini), 6.1-inch (standard), 6.7-inch (Plus/Max)",
            "Face ID vs Touch ID (SE) — authentication must work on both",
            "Gesture navigation: swipe from bottom edge (no home button models) must not conflict with app gestures",
            "Permissions: camera, photos, location (always/when in use/never), notifications — grant and deny",
            "App lifecycle: background→foreground, app switch, force quit→relaunch",
            "Push notifications: APNs delivery, banner/alert/badge behavior, tap-to-open action",
            "Dark mode (iOS 13+): UI must render correctly in both system themes",
            "Dynamic Type: test with small, default, large, and accessibility XL font sizes",
            "Network conditions: WiFi, 5G, 4G LTE, 3G, airplane mode transitions",
            "Crash recovery: app must resume from last valid state after crash"
        ],

        "hybrid app": [
            "WebView rendering: test on Android WebView (Chromium-based) and iOS WKWebView separately",
            "Native-to-web bridge: JavaScript calls from native must not time out or silently fail",
            "OS versions: same coverage as Android app + iOS app — test minimum 3 versions each",
            "Device brands: same as Android app section above",
            "Web content responsiveness inside native wrapper — no overflow or clipped content",
            "Offline sync: WebView cached content vs native offline handling must be consistent",
            "App update compatibility: old cached WebView content must not persist after update",
            "Permission handling: camera/storage/location via both native and WebView bridges"
        ],

        "api": [
            "HTTP status codes: 200, 201, 400, 401, 403, 404, 409, 422, 429, 500, 503 — each must be verified",
            "Response schema validation: required fields, data types, null handling",
            "Authentication: valid token, expired token, missing token, tampered token",
            "Invalid payloads: missing required fields, wrong types, oversized values, SQL/injection strings",
            "Rate limiting: test at limit boundary (N-1, N, N+1 requests per window)",
            "Pagination: first page, last page, out-of-range page, empty result",
            "Idempotency: repeated POST/PUT with same data must not create duplicates",
            "Backward compatibility: older clients must not break after version bump",
            "Response time: under 200ms for reads, under 500ms for writes (baseline)"
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
            "Typo/partial keyword handling",
            "Autosuggest relevance and de-duplication",
            "Category and company intent matching",
            "Result relevance and ranking consistency",
            "Pagination and infinite-scroll consistency",
            "Recent search persistence and recall",
            "Performance with large dataset"
        ],
        "catalogue": [
            "Category hierarchy rendering accuracy",
            "Vertical-specific listing correctness",
            "Applied filters reflected correctly in results",
            "Navigation state retained when returning from details"
        ],
        "verticals": [
            "Cross-vertical navigation consistency",
            "Context switch behavior between vertical journeys",
            "Vertical-specific metadata visibility and validation"
        ],
        "profile": [
            "Business profile data completeness",
            "Phone/address/email action behavior",
            "Back navigation to source listing consistency"
        ],
        "payment gateway": [
            "Payment option visibility and validity",
            "Failure/retry behavior for payment attempts",
            "Transaction status reconciliation"
        ],
        "reviews ratings": [
            "Rating aggregation accuracy",
            "Review sorting and filtering correctness",
            "Fraud/spam moderation visibility behavior"
        ],
        "chatbot": [
            "Intent recognition accuracy for search-related prompts",
            "Fallback response quality for unsupported queries",
            "Conversation context continuity"
        ],
        "kyc": [
            "Document age validation: >2 years from upload date triggers alert and delete",
            "Alert warning popup must appear before any KYC action when aged document detected",
            "Category-wise handling: NON-RC, RC, SRC, JdPay KYC, JdPay Omni differ in rules",
            "Approved document associated with live contract must be flagged and deleted",
            "Unverified/Unapproved documents >2 years must be deleted for Inactive contracts",
            "ID Proof, Address Proof, Business Proof, Shop Images each have independent age checks",
            "RC/SRC: only the latest actioned document (ID/Address/Business Proof) triggers alert if >2 years",
            "Shop images >2 years and Approved: same alert-and-delete flow as RC/SRC proofs",
            "Document vintage must be shown in the alert message (exact upload date or age)",
            "Delete action must reflect immediately in UI without page reload",
            "Paid and Non-Paid contracts both in scope for document age checks",
            "JdPay KYC and JdPay Omni contracts require separate verification pass",
            "Inactive contract: delete even Unverified/Unapproved documents if >2 years"
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
            "Result count and relevance accuracy",
            "Filter/sort impact reflected in listing order",
            "Pagination or infinite scroll control validation",
            "No-result and weak-network messaging"
        ],
        "details page": [
            "Listing vs details data consistency",
            "Business contact data consistency",
            "Address/location consistency",
            "Ratings/reviews summary consistency",
            "Back navigation consistency"
        ],
        "profile page": [
            "Profile information display correctness",
            "Profile edit save/cancel behavior",
            "Logout and session handling behavior"
        ],
        "user profile page": [
            "Profile information display correctness",
            "Profile edit save/cancel behavior",
            "Logout and session handling behavior"
        ],
        "reviews ratings": [
            "Review visibility and ordering consistency",
            "Rating distribution accuracy",
            "Review pagination/load more behavior"
        ],
        "edit listings page": [
            "Editable fields validation and constraints",
            "Draft vs published state handling",
            "Change history visibility consistency"
        ],
        "payment gateway page": [
            "Payment method option correctness",
            "Payment failure/retry behavior",
            "Final status display consistency"
        ],
        "kyc": [
            "Alert popup appears on KYC page load when any document is >2 years old",
            "Alert message shows exact document type, upload date/vintage, and contract category",
            "Delete CTA visible only for documents that meet the >2yr deletion criteria",
            "Document list reflects deletion immediately without page reload",
            "After deletion, re-upload option is available and document returns as Unverified",
            "No alert shown for documents ≤ 2 years regardless of status",
            "Category sections clearly distinguish NON-RC, RC, SRC, JdPay documents",
            "Document status badges (Approved/Unapproved/Unverified/Rejected) correctly rendered",
            "Boundary: document exactly 2 years old — no alert, no delete option",
            "Boundary: document 2 years + 1 day old — alert and delete option must appear",
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


def build_context_block(platforms, modules, pages, classification=None, actor_scope="user"):
    """
    Context builder only.
    No classification logic inside.
    Optionally classification-aware for scope emphasis.
    actor_scope: "user" | "admin" | "e2e" — filters KYC admin pointers accordingly.
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

    # KYC actor-scope filtering: inject admin pointers only when scope warrants it
    kyc_in_scope = any(
        _normalize(m) == "kyc" for m in (modules or [])
    ) or any(
        _normalize(p) == "kyc" for p in (pages or [])
    )
    if kyc_in_scope:
        if actor_scope in ("admin", "e2e"):
            classification_context += """
KYC Admin/Backend Scope (included because scope is admin or e2e):
- Admin can Approve / Unapprove / Reject / Reverify any document
- Reverify resets document to Unverified and re-enters verification queue
- Reupload request sent to user after admin Rejects or triggers Reupload action
- Admin panel must reflect user-side deletions immediately
- Backend must enforce age-check rule independently of UI
"""
        if actor_scope == "user":
            classification_context += """
KYC Scope Note: User-facing only. Admin panel and backend verification steps excluded unless explicitly required.
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
