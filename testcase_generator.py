import json
import re
import uuid
from collections import Counter
from ai_service import ask_ai
from memory.memory_engine import get_patterns_for_requirement, store_patterns
from context_builder import build_context_block


JUSTDIAL_DOMAIN_KEYWORDS = {
    "justdial",
    "category",
    "company",
    "vertical",
    "verticals",
    "flight",
    "b2b",
    "movie",
    "pg",
    "edit listing",
    "profile",
    "review",
    "rating",
    "search",
    "result page",
    "details page",
    "pdp",
    "prp",
    "catalogue",
}

KYC_DOMAIN_KEYWORDS = {
    "kyc", "document", "id proof", "address proof", "business proof",
    "shop image", "shop images", "rc", "non-rc", "non rc", "src",
    "jdpay", "jd pay", "reverify", "re-verify", "reupload", "re-upload",
    "approved", "unapproved", "unverified", "vintage",
    "kyc document", "document approval", "contract live", "live contract",
    "document verification", "reverification",
}

# Actor scope keyword sets
ADMIN_SCOPE_KEYWORDS = {
    "admin", "admin panel", "backend", "operations", "ops", "crm",
    "internal tool", "cs agent", "support agent", "dc", "de",
}
USER_SCOPE_KEYWORDS = {
    "frontend tester", "business owner", "merchant", "client",
    "customer", "end user", "fe tester", "user side", "user facing",
}
E2E_SCOPE_KEYWORDS = {
    "e2e", "end to end", "end-to-end", "complete flow", "full flow",
    "cross-system", "integration flow",
}

# Document lifecycle: current_status -> possible next transitions
DOCUMENT_LIFECYCLE = {
    "Approved": ["Rejected", "Reverify", "Reupload"],
    "Unapproved": ["Reverify", "Reupload"],
    "Unverified": ["Approved", "Unapproved", "Rejected"],
    "Rejected": ["Reupload"],
}

COMMERCE_KEYWORDS = {
    "cart",
    "checkout",
    "shipping",
    "delivery",
    "order",
    "coupon",
    "payment",
    "inventory",
}

SESSION_STATE_KEYWORDS = {
    "session",
    "state",
    "resume",
    "relaunch",
    "re-open",
    "app relaunch",
    "last searched",
    "last visited",
    "recent search",
    "continue where left",
    "restore",
}

DOMAIN_KEY_CATALOG = [
    "justdial",
    "search",
    "category",
    "company",
    "vertical",
    "flight",
    "b2b",
    "movie",
    "pg",
    "edit listing",
    "profile",
    "review",
    "rating",
    "result page",
    "details page",
    "last searched",
    "last visited",
    "session",
    "relaunch",
]

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "when", "where",
    "into", "only", "must", "should", "have", "has", "are", "was", "were",
    "will", "would", "could", "can", "after", "before", "user", "users",
    "page", "pages", "test", "tests", "case", "cases", "verify", "validate",
}

GENERIC_SCENARIO_MARKERS = {
    "validate functionality",
    "verify functionality",
    "validate system behavior",
    "verify system behavior",
    "check functionality",
    "test functionality",
    "general validation",
}

# entity keywords + forbidden terms + recommended replacement
INVALID_DOMAIN_COMBOS = [
    ({"restaurant", "dining", "food"}, {"ticket", "tickets", "showtime", "seat"}, "table reservation"),
    ({"movie", "cinema", "film"}, {"appointment", "appointments"}, "ticket booking"),
    ({"flight", "airline"}, {"appointment", "appointments"}, "ticket booking"),
    ({"doctor", "clinic", "hospital"}, {"ticket", "tickets", "showtime", "seat"}, "appointment booking"),
]


def _normalize_for_keyword_match(text: str) -> str:
    return re.sub(r"[_\-]+", " ", (text or "").lower())


def _contains_keyword(text: str, keyword: str) -> bool:
    """
    Safe keyword match with token boundaries.
    Prevents false matches like 'rc' inside 'search'.
    """
    normalized_text = _normalize_for_keyword_match(text)
    normalized_keyword = _normalize_for_keyword_match(keyword).strip()
    if not normalized_keyword:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def _matches_any_keyword(text: str, keywords: set[str]) -> bool:
    return any(_contains_keyword(text, kw) for kw in keywords)


def _infer_domain(requirement: str, modules: list, pages: list) -> str:
    bag = " ".join(
        [requirement or ""] + [str(m) for m in modules or []] + [str(p) for p in pages or []]
    ).lower()

    # Prefer Justdial/search domain when explicit markers are present.
    if _matches_any_keyword(bag, JUSTDIAL_DOMAIN_KEYWORDS):
        return "directory_search"

    if _matches_any_keyword(bag, KYC_DOMAIN_KEYWORDS):
        return "kyc"

    if _matches_any_keyword(bag, COMMERCE_KEYWORDS):
        return "commerce"

    return "generic"


def _detect_actor_scope(requirement: str, test_types: list) -> str:
    """
    Detect whether the requirement is user-facing, admin-facing, or e2e.
    E2E always wins — it must include both user and admin flows.
    """
    text = requirement.lower()
    types_text = " ".join(t.lower() for t in (test_types or []))

    if any(kw in text or kw in types_text for kw in E2E_SCOPE_KEYWORDS):
        return "e2e"
    if "e2e" in types_text:
        return "e2e"
    if any(kw in text for kw in ADMIN_SCOPE_KEYWORDS):
        return "admin"
    # Default to user-facing when requirement mentions user roles or is frontend-scoped
    return "user"


def _build_kyc_domain_block(requirement: str, actor_scope: str) -> str:
    """
    Builds a KYC-specific guidance block for the prompt.
    Conditionally includes admin pointers only for admin/e2e scope.
    """
    text = requirement.lower()

    # Detect which contract categories are mentioned
    categories = []
    if "non-rc" in text or "non rc" in text:
        categories.append("NON-RC")
    if "src" in text:
        categories.append("SRC")
    # Match standalone "rc" — exclude "non-rc" and "src" (lookbehind for "non-" and any [a-z])
    if re.search(r"(?<!non-)(?<![a-z])rc(?![a-z])", text):
        categories.append("RC")
    if "jdpay" in text or "jd pay" in text:
        categories.append("JdPay KYC / JdPay Omni")
    if not categories:
        categories = ["RC", "NON-RC", "SRC"]  # default to all if none specified

    # Detect which document types are mentioned
    doc_types = []
    if "id proof" in text or "id / address" in text:
        doc_types.append("ID Proof")
    if "address proof" in text or "id / address" in text:
        doc_types.append("Address Proof")
    if "business proof" in text:
        doc_types.append("Business Proof")
    if "shop image" in text:
        doc_types.append("Shop Images")
    if not doc_types:
        doc_types = ["ID Proof", "Address Proof", "Business Proof", "Shop Images"]

    # Detect which statuses are mentioned
    statuses = []
    if "approved" in text:
        statuses.append("Approved")
    if "unapproved" in text:
        statuses.append("Unapproved")
    if "unverified" in text:
        statuses.append("Unverified")
    if "rejected" in text:
        statuses.append("Rejected")
    if not statuses:
        statuses = list(DOCUMENT_LIFECYCLE.keys())

    # Build lifecycle transitions for detected statuses
    lifecycle_lines = []
    for status in statuses:
        transitions = DOCUMENT_LIFECYCLE.get(status, [])
        if transitions:
            lifecycle_lines.append(
                f"  - {status} document → post-delete/action transitions: {', '.join(transitions)}"
            )

    # Age boundary combinations
    age_combos = [
        "Document uploaded exactly 2 years ago (boundary - should NOT trigger)",
        "Document uploaded 2 years + 1 day ago (boundary - MUST trigger)",
        "Document uploaded 3 years ago (clearly > 2 yrs)",
        "Document uploaded 1 year ago (clearly ≤ 2 yrs - no action)",
    ]

    user_block = f"""
KYC Domain Active. Contract categories in scope: {', '.join(categories)}
Document types in scope: {', '.join(doc_types)}
Document statuses in scope: {', '.join(statuses)}

Document Lifecycle — Generate test cases for EACH state transition:
{chr(10).join(lifecycle_lines)}

Age Boundary Combinations (mandatory coverage):
{chr(10).join(f'  - {c}' for c in age_combos)}

User-Facing KYC Rules to test:
- Alert warning popup appears on KYC page load when aged document is found
- Alert message must display the document vintage (upload date or age)
- Alert is category-specific: different message per NON-RC / RC / SRC / JdPay
- Delete action on aged Approved doc (live contract): confirm → doc removed from UI immediately
- Delete action on aged Unverified/Unapproved doc (inactive contract): same immediate removal
- After delete: user can re-upload → document goes back to Unverified state
- No alert for documents ≤ 2 years regardless of status
- Paid and Non-Paid contracts both show alert when aged doc is found
- JdPay KYC and JdPay Omni: must also show alert for aged documents (separate check)
"""

    admin_block = """
Admin/Backend KYC Rules to test (include for E2E and Admin scope):
- Admin can Approve / Unapprove / Reject any document regardless of age
- Reverify action resets document to Unverified, re-enters verification queue
- Reupload request sent to user after admin Rejects or triggers Reupload
- Admin approval of an aged document (>2 yrs) should NOT override the age-deletion rule
- Backend API must enforce age check independently — UI delete must reflect API-level deletion
- Inactive contract: system auto-deletes >2yr Unverified/Unapproved even without admin action
"""

    if actor_scope == "user":
        return user_block
    elif actor_scope == "admin":
        return user_block + admin_block
    else:  # e2e
        return user_block + admin_block + """
E2E Cross-System Validations:
- User sees alert on KYC page → deletes doc → admin panel reflects deletion immediately
- Admin rejects doc → user receives reupload prompt on KYC page
- User reuploads → doc returns as Unverified in both UI and admin panel
- Contract live status changes correctly after aged document is deleted
"""


PLATFORM_MANDATORY_SCENARIOS = {
    "android_app": {
        "label": "Android App",
        "os_versions": ["Android 8 (Oreo)", "Android 10", "Android 12", "Android 14"],
        "devices": ["Samsung Galaxy A/S series", "Xiaomi Redmi/Note", "OnePlus", "POCO/Realme"],
        "resolutions": ["HD 720p", "FHD 1080p", "FHD+ 1080x2400"],
        "mandatory": [
            "Test on minimum Android 8 AND Android 12+ (gesture nav vs button nav)",
            "Test on low-RAM device (2-3GB) for memory pressure scenarios",
            "Test Samsung Galaxy AND Xiaomi — manufacturer skin differences",
            "Verify app on FHD 1080p and HD 720p screens",
            "Test runtime permission: grant AND deny (camera/storage/location)",
            "Test background→foreground app switch — state must be preserved",
            "Test app kill → relaunch — must restore to last valid state",
            "Test Dark mode (Android 10+): system setting ON and OFF",
            "Test with accessibility font size at 130% and 200%",
        ],
    },
    "ios_app": {
        "label": "iOS App",
        "os_versions": ["iOS 15", "iOS 16", "iOS 17", "iOS 18"],
        "devices": ["iPhone SE (home button)", "iPhone 13/14 (notch)", "iPhone 15 Pro (Dynamic Island)", "iPhone 14/15 Plus (large)"],
        "resolutions": ["4.7-inch (SE)", "6.1-inch (standard)", "6.7-inch (Plus/Max)"],
        "mandatory": [
            "Test on iOS 15 AND iOS 17+ — API behavior differences",
            "Test iPhone SE (small screen, home button) AND iPhone 14/15 Pro (Dynamic Island)",
            "Test Face ID AND Touch ID (SE) authentication",
            "Test gesture navigation (swipe-from-bottom) does not conflict with app swipes",
            "Test permission: grant AND deny AND 'when in use' for camera/location/notifications",
            "Test background→foreground and force quit→relaunch state restoration",
            "Test Dark mode ON and OFF",
            "Test Dynamic Type: small font AND accessibility XL font",
        ],
    },
    "web": {
        "label": "Web",
        "browsers": ["Chrome 120+", "Firefox 120+", "Edge 120+", "Safari 16+"],
        "resolutions": ["1366x768", "1920x1080", "1440x900", "1280x800"],
        "mandatory": [
            "Test on Chrome AND Firefox AND Safari — rendering must be consistent",
            "Test on 1920x1080 AND 1366x768 (most common laptop resolution)",
            "Test at 100% zoom AND 125% zoom — layout must not break",
            "Test on Windows AND macOS (Safari-specific rendering may differ)",
            "Test with cleared cache AND expired session",
            "Test keyboard-only navigation (Tab, Enter, Escape)",
            "Test incognito / private browsing mode",
            "Test browser back/forward navigation — page state must be preserved",
        ],
    },
    "touch": {
        "label": "Mobile Web (Touch)",
        "browsers": ["Chrome for Android", "Safari for iOS", "Samsung Internet", "Firefox Mobile"],
        "resolutions": ["5.4-inch", "6.1-inch", "6.7-inch"],
        "mandatory": [
            "Test on Android Chrome AND iOS Safari — rendering differs significantly",
            "Test on Samsung Internet (Samsung devices have it as default)",
            "Test portrait AND landscape orientation — layout must reflow",
            "Test with virtual keyboard open — form inputs must not be hidden",
            "Test on 3G/slow network — graceful degradation required",
            "Test pinch-to-zoom and double-tap behavior",
            "Test iOS Safari bounce scroll — must not cause UI breakage",
        ],
    },
    "hybrid_app": {
        "label": "Hybrid App",
        "mandatory": [
            "Test Android WebView (Chromium) AND iOS WKWebView separately",
            "Test OS version range: same as Android App + iOS App coverage",
            "Test native→web bridge: JavaScript callbacks must not time out",
            "Test offline mode: WebView cached content vs native fallback",
            "Test after app update: cached WebView content must be invalidated",
            "Test on low-RAM Android (2GB) — WebView memory pressure",
        ],
    },
    "api": {
        "label": "API",
        "mandatory": [
            "Test HTTP 200, 400, 401, 403, 404, 422, 429, 500 response codes",
            "Test with expired token AND missing token AND tampered token",
            "Test rate limit boundary: N-1 requests (pass), N+1 requests (throttled)",
            "Test idempotency: same request sent twice must not duplicate data",
            "Test pagination: page 1, last page, out-of-range page",
            "Test response schema: all required fields present, correct types",
        ],
    },
}

PLATFORM_KEY_MAP = {
    "android_app": "android_app",
    "android app": "android_app",
    "androidapp": "android_app",
    "ios_app": "ios_app",
    "ios app": "ios_app",
    "iosapp": "ios_app",
    "web": "web",
    "touch": "touch",
    "mobile web": "touch",
    "hybrid_app": "hybrid_app",
    "hybrid app": "hybrid_app",
    "api": "api",
    "backend": "api",
}

CROSS_PLATFORM_HANDOFF_KEYWORDS = {
    "cross platform",
    "cross-platform",
    "handoff",
    "handover",
    "share",
    "shared",
    "open in app",
    "continue in app",
    "deep link",
    "deeplink",
    "universal link",
    "app link",
}

PLATFORM_TITLE_DETAIL_KEYWORDS = {
    "android", "ios", "chrome", "firefox", "safari", "edge", "opera",
    "windows", "macos", "ubuntu", "samsung", "xiaomi", "oneplus", "iphone",
    "ipad", "resolution", "zoom", "ram", "fhd", "qhd", "hd", "inch", "dynamic island"
}


def _normalize_platform_keys(platforms: list) -> list[str]:
    matched: list[str] = []
    for platform in platforms or []:
        normalized = str(platform).strip().lower().replace("-", " ").replace("_", " ")
        key = PLATFORM_KEY_MAP.get(normalized) or PLATFORM_KEY_MAP.get(str(platform).lower())
        if key and key not in matched:
            matched.append(key)
    return matched


def _is_cross_platform_handoff_requirement(requirement: str) -> bool:
    requirement_text = (requirement or "").lower()
    return any(keyword in requirement_text for keyword in CROSS_PLATFORM_HANDOFF_KEYWORDS)


def _build_platform_scope_text(platforms: list) -> str:
    keys = _normalize_platform_keys(platforms)
    if not keys:
        return "selected platform"
    labels = [
        PLATFORM_MANDATORY_SCENARIOS.get(key, {}).get("label", key.replace("_", " ").title())
        for key in keys
    ]
    return ", ".join(labels)


def _build_platform_instruction_block(platforms: list, allow_cross_platform_handoff: bool = False) -> str:
    """
    Builds a mandatory platform-specific instruction block.
    Goes into the prompt BODY (not just context hints) to force platform-aware test cases.
    Enforces cross-platform isolation when multiple platforms are selected.
    """
    if not platforms:
        return ""

    matched = _normalize_platform_keys(platforms)

    if not matched:
        return ""

    lines = ["\nPlatform-Specific Test Requirements (MANDATORY — not optional hints):"]

    for key in matched:
        spec = PLATFORM_MANDATORY_SCENARIOS.get(key)
        if not spec:
            continue
        label = spec["label"]
        lines.append(f"\n[{label}]")
        for rule in spec["mandatory"]:
            lines.append(f"- {rule}")
        # Add device/OS version specifics where available
        if "os_versions" in spec:
            lines.append(f"  OS versions to cover: {', '.join(spec['os_versions'])}")
        if "devices" in spec:
            lines.append(f"  Device types to cover: {', '.join(spec['devices'])}")
        if "browsers" in spec:
            lines.append(f"  Browsers to cover: {', '.join(spec['browsers'])}")
        if "resolutions" in spec:
            lines.append(f"  Screen resolutions to cover: {', '.join(spec['resolutions'])}")

    lines.append("\nPlatform Test Case Rules:")
    if len(matched) > 1:
        platform_labels = [PLATFORM_MANDATORY_SCENARIOS[k]["label"] for k in matched if k in PLATFORM_MANDATORY_SCENARIOS]
        lines.append(f"- Multiple platforms selected: {', '.join(platform_labels)}")
        lines.append("- Default rule: generate separate test cases per platform")
        lines.append("- Do NOT mix unrelated Android/iOS/Web actions in one testcase")
        lines.append("- Label each test case with target platform in title (e.g., '[Android] ...', '[iOS] ...', '[Web] ...')")
        lines.append("- A test case for Android must only reference Android OS versions, Android browsers, Android device brands")
        lines.append("- A test case for iOS must only reference iOS versions, iOS devices, Safari/iOS Chrome")
        lines.append("- Use specific device/browser/OS names only in representative coverage cases (~20-30% cases), not in every testcase title")
        lines.append("- Keep most scenario titles concise and human-readable; avoid long device matrix text in titles")
        lines.append("- Exception: cross-platform mixing is allowed ONLY for explicit handoff journeys, and must be labeled '[Cross-Platform] Source -> Target'")
        lines.append("- Cross-platform cases must keep clean source->target transitions (e.g., web share link -> app open), no domain/platform contradiction")
        if allow_cross_platform_handoff:
            lines.append("- Requirement explicitly asks cross-platform behavior: generate at least one dedicated handoff testcase per logical selected platform pair")
            if "web" in matched and "android_app" in matched:
                lines.append("- Mandatory handoff pair: Web -> Android App via shared/deep link")
            if "web" in matched and "ios_app" in matched:
                lines.append("- Mandatory handoff pair: Web -> iOS App via shared/deep link")
            if "touch" in matched and "android_app" in matched:
                lines.append("- Mandatory handoff pair: Mobile Web -> Android App")
            if "touch" in matched and "ios_app" in matched:
                lines.append("- Mandatory handoff pair: Mobile Web -> iOS App")
    else:
        label = PLATFORM_MANDATORY_SCENARIOS[matched[0]]["label"] if matched[0] in PLATFORM_MANDATORY_SCENARIOS else matched[0]
        lines.append(f"- Single platform selected: {label}")
        lines.append(f"- Mention explicit {label} OS/device/browser details in selected representative cases only (~20-30% cases)")
        lines.append(f"- Keep remaining titles natural and concise; avoid adding long hardware/browser suffixes to every case title")
        lines.append(f"- Do NOT write generic steps — include concrete platform validation where relevant")

    return "\n".join(lines) + "\n"


def _is_session_state_requirement(requirement: str, classification: dict) -> bool:
    requirement_text = (requirement or "").lower()
    include_layers = classification.get("include_layers", [])
    return (
        "state" in include_layers
        or "session" in include_layers
        or any(keyword in requirement_text for keyword in SESSION_STATE_KEYWORDS)
    )


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _extract_unique_domain_keys(existing_cases, requirement, modules, pages):
    corpus = [
        requirement or "",
        " ".join(str(m) for m in (modules or [])),
        " ".join(str(p) for p in (pages or [])),
    ]

    for case in existing_cases or []:
        corpus.append(str(case.get("scenario", "")))
        corpus.append(" ".join(str(s) for s in case.get("steps", []) if isinstance(s, str)))
        corpus.append(str(case.get("expected_result", "")))

    blob = _normalize_text(" ".join(corpus))

    explicit_keys = [key for key in DOMAIN_KEY_CATALOG if key in blob]
    if explicit_keys:
        return sorted(set(explicit_keys))

    tokens = re.findall(r"[a-z][a-z0-9_]{2,}", blob)
    token_counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [token for token, _ in token_counts.most_common(20)]


def _build_update_mode_block(existing_cases, update_comment, unique_keys):
    if not existing_cases:
        return ""

    return f"""
Update Mode Inputs:
- Existing uploaded test cases count: {len(existing_cases)}
- User update comment: {update_comment or "N/A"}
- Extracted domain keys from existing cases: {unique_keys}

Hard Constraints for update mode:
- Reuse domain keys above as anchor entities.
- Do not introduce unrelated domains.
- Maintain action-entity consistency.
- Invalid examples to avoid:
  - restaurant + ticket booking
  - movie + appointment booking
"""


def _contains_invalid_domain_combo(text: str) -> bool:
    normalized = _normalize_text(text)
    for entities, invalid_terms, _ in INVALID_DOMAIN_COMBOS:
        if any(entity in normalized for entity in entities) and any(term in normalized for term in invalid_terms):
            return True
    return False


def _repair_domain_text(text: str) -> str:
    updated = text or ""
    normalized = _normalize_text(updated)

    replacement_rules = [
        (r"\brestaurant\b.*\b(tickets?|showtime|seat)\b", "restaurant table reservation"),
        (r"\b(movie|cinema|film)\b.*\bappointments?\b", "movie ticket booking"),
        (r"\b(flight|airline)\b.*\bappointments?\b", "flight ticket booking"),
        (r"\b(doctor|clinic|hospital)\b.*\b(tickets?|showtime|seat)\b", "doctor appointment booking"),
    ]

    for pattern, replacement in replacement_rules:
        if re.search(pattern, normalized):
            return replacement

    return updated


def _replace_terms(text: str, terms: set[str], replacement: str) -> str:
    updated = text
    for term in sorted(terms, key=len, reverse=True):
        updated = re.sub(rf"\b{re.escape(term)}\b", replacement, updated, flags=re.IGNORECASE)
    return updated


def _repair_case_domain_mismatch(scenario: str, steps: list[str], expected_result: str):
    combined = _normalize_text(" ".join([scenario, " ".join(steps), expected_result]))

    for entities, invalid_terms, replacement in INVALID_DOMAIN_COMBOS:
        if any(entity in combined for entity in entities) and any(term in combined for term in invalid_terms):
            scenario = _replace_terms(scenario, invalid_terms, replacement)
            steps = [_replace_terms(step, invalid_terms, replacement) for step in steps]
            expected_result = _replace_terms(expected_result, invalid_terms, replacement)
            combined = _normalize_text(" ".join([scenario, " ".join(steps), expected_result]))

    return scenario, steps, expected_result


def _deduplicate_with_existing(generated_cases, existing_cases):
    existing_scenarios = {
        _normalize_text(str(case.get("scenario", "")))
        for case in (existing_cases or [])
        if isinstance(case, dict)
    }

    seen = set()
    unique = []
    for case in generated_cases:
        if not isinstance(case, dict):
            continue
        scenario_key = _normalize_text(str(case.get("scenario", "")))
        if not scenario_key:
            continue
        if scenario_key in existing_scenarios:
            continue
        if scenario_key in seen:
            continue
        seen.add(scenario_key)
        unique.append(case)
    return unique


def _compact_steps(steps: list[str]) -> list[str]:
    compacted = []
    seen = set()
    for step in steps or []:
        cleaned = str(step).strip()
        if not cleaned:
            continue
        key = _normalize_text(cleaned)
        if key in seen:
            continue
        seen.add(key)
        compacted.append(cleaned)
    return compacted


def _is_junk_case(scenario: str, steps: list[str], expected_result: str) -> bool:
    scenario_norm = _normalize_text(scenario)
    expected_norm = _normalize_text(expected_result)

    if not scenario_norm or scenario_norm in GENERIC_SCENARIO_MARKERS:
        return True

    # Reject ultra-generic placeholders.
    if scenario_norm in {"n/a", "na", "test case", "scenario"}:
        return True

    # Require minimally informative scenario text.
    if len(scenario_norm) < 12:
        return True

    # Avoid empty/near-empty steps even before integrity fallback.
    valid_steps = [s for s in steps if _normalize_text(s)]
    if len(valid_steps) < 2:
        return True

    # Avoid generic expected results that add no signal.
    if expected_norm in {"ok", "success", "works", "as expected", "pass"}:
        return True

    return False


def _deduplicate_across_categories(positive: list[dict], negative: list[dict]):
    """
    Prevent near-identical scenarios appearing in both positive and negative buckets.
    Keep first occurrence to avoid repetition noise.
    """
    seen = set()
    p_out = []
    n_out = []

    for case in positive:
        key = _normalize_text(str(case.get("scenario", "")))
        if not key or key in seen:
            continue
        seen.add(key)
        p_out.append(case)

    for case in negative:
        key = _normalize_text(str(case.get("scenario", "")))
        if not key or key in seen:
            continue
        seen.add(key)
        n_out.append(case)

    return p_out, n_out


def _extract_trailing_parenthetical(text: str) -> str:
    match = re.search(r"\(([^()]*)\)\s*$", text or "")
    return match.group(1).strip() if match else ""


def _is_over_detailed_platform_suffix(scenario: str) -> bool:
    tail = _extract_trailing_parenthetical(scenario)
    if not tail:
        return False
    lowered = tail.lower()
    keyword_hits = sum(1 for kw in PLATFORM_TITLE_DETAIL_KEYWORDS if kw in lowered)
    return (tail.count(",") >= 2 and keyword_hits >= 2) or (len(tail) >= 60 and keyword_hits >= 1)


def _humanize_scenario_title(scenario: str, keep_detailed: bool = False) -> str:
    cleaned = (scenario or "").strip()
    if not cleaned or keep_detailed:
        return cleaned

    if _is_over_detailed_platform_suffix(cleaned):
        cleaned = re.sub(r"\s*\([^()]*\)\s*$", "", cleaned).strip()

    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.rstrip(" -,:;")


def _sanitize_generated_cases(testcases: dict, existing_cases=None, requirement: str = "") -> dict:
    positive = []
    negative = []
    detailed_title_kept = 0

    for source, target in [
        (testcases.get("positive_tests", []), positive),
        (testcases.get("negative_tests", []), negative),
    ]:
        for case in source:
            if not isinstance(case, dict):
                continue

            scenario = _repair_domain_text(str(case.get("scenario", "")))
            if _is_over_detailed_platform_suffix(scenario):
                keep_detailed = detailed_title_kept < 2
                if keep_detailed:
                    detailed_title_kept += 1
                scenario = _humanize_scenario_title(scenario, keep_detailed=keep_detailed)
            else:
                scenario = _humanize_scenario_title(scenario)
            steps = [
                _repair_domain_text(str(step))
                for step in (case.get("steps", []) or [])
                if str(step).strip()
            ]
            steps = _compact_steps(steps)
            expected_result = _repair_domain_text(str(case.get("expected_result", "")))
            scenario, steps, expected_result = _repair_case_domain_mismatch(
                scenario,
                steps,
                expected_result,
            )

            combined = " ".join([scenario, " ".join(steps), expected_result]).strip()
            if _contains_invalid_domain_combo(combined):
                continue
            if _is_junk_case(scenario, steps, expected_result):
                continue

            case["scenario"] = scenario
            case["steps"] = steps
            case["expected_result"] = expected_result
            target.append(case)

    positive = _deduplicate_with_existing(positive, existing_cases)
    negative = _deduplicate_with_existing(negative, existing_cases)
    positive, negative = _deduplicate_across_categories(positive, negative)

    if not positive and not negative:
        return _fallback_basic_cases(requirement or "Domain-consistent update scenario")

    if not positive:
        positive.append({
            "testcase_id": f"TC_{uuid.uuid4().hex[:6].upper()}",
            "priority": "Medium",
            "scenario": "Validate domain-consistent primary workflow",
            "steps": [
                "Launch app and open intended module",
                "Execute domain-specific user journey",
                "Verify expected state and data consistency"
            ],
            "expected_result": "Workflow completes with correct domain behavior and no cross-domain mismatch."
        })

    return {
        "positive_tests": positive,
        "negative_tests": negative,
    }


def generate_testcases(analysis_json, existing_cases=None, update_comment=None):

    # feature = short AI-extracted name (used for memory, dedup, fallback labels)
    # original_requirement = full original text (used for detection, domain inference, prompt)
    requirement = analysis_json.get("feature", "")
    original_requirement = analysis_json.get("_original_requirement") or requirement

    test_types = analysis_json.get("test_types", [])

    platforms = analysis_json.get("platforms", [])
    modules = analysis_json.get("modules", [])
    pages = analysis_json.get("pages", [])

    classification = analysis_json.get("_classification", {})
    mode = classification.get("mode", "inferred")
    classified_type = classification.get("type", "unknown")
    confidence = classification.get("confidence", 0)

    # Use full original text for all detection — feature name is too compressed
    domain = _infer_domain(original_requirement, modules, pages)
    actor_scope = _detect_actor_scope(original_requirement, test_types)
    is_session_state_flow = _is_session_state_requirement(original_requirement, classification)
    is_cross_platform_handoff_flow = _is_cross_platform_handoff_requirement(original_requirement)
    normalized_platforms = _normalize_platform_keys(platforms)
    has_app_platform = any(p in {"android_app", "ios_app", "hybrid_app"} for p in normalized_platforms)
    has_web_platform = any(p in {"web", "touch"} for p in normalized_platforms)
    unique_domain_keys = _extract_unique_domain_keys(existing_cases, original_requirement, modules, pages)

    memory_patterns = get_patterns_for_requirement(requirement)
    context_block = build_context_block(platforms, modules, pages, classification, actor_scope)
    platform_instruction_block = _build_platform_instruction_block(
        platforms,
        allow_cross_platform_handoff=is_cross_platform_handoff_flow
    )
    platform_scope_text = _build_platform_scope_text(platforms)

    # -----------------------------------------
    # CLASSIFICATION-DRIVEN GENERATION LOGIC
    # -----------------------------------------

    classification_guidance = ""

    if mode == "strict":
        classification_guidance += f"""
STRICT MODE ACTIVATED (PS-ONLY).
Focus ONLY on these layers:
{classification.get("include_layers", [])}
Do NOT generate unrelated test scenarios.
"""
        if is_session_state_flow:
            classification_guidance += """
This is a STATE/SESSION-focused strict request.
Generate ONLY session/state continuity validations:
- App relaunch state restoration
- Last searched query restoration
- Last visited page restoration
- Back-stack/session invalidation behavior
Do NOT include cart/checkout/order/payment coverage unless explicitly requested.
"""
    else:
        if classified_type == "performance":
            classification_guidance += """
Emphasize performance testing:
- Load handling
- Response time validation
- Stress behavior
- Concurrency handling
"""
        elif classified_type == "security":
            classification_guidance += """
Emphasize security testing:
- Authentication checks
- Authorization validation
- Token/session handling
- Data encryption validation
- Input tampering tests
"""
        elif classified_type == "api":
            classification_guidance += """
Emphasize API-level validation:
- Status codes
- Request/response validation
- Contract validation
- Schema checks
- Error codes
"""
        elif classified_type == "ui":
            classification_guidance += """
Emphasize UI validation:
- Layout validation
- Field validation
- Navigation flow
- Error messages
- Responsive behavior
"""
        elif classified_type == "multi_scope":
            classification_guidance += """
This is a multi-layer requirement.
Generate comprehensive cross-layer validation.
"""
        elif classified_type == "unknown":
            classification_guidance += """
Requirement classification is unclear.
Generate balanced coverage across possible scenarios.
"""

    # -----------------------------------------
    # PROMPT
    # -----------------------------------------

    notification_keywords = [
        "sms",
        "whatsapp",
        "push notification",
        "push notifications",
        "push",
        "otp",
        "one time password",
        "verification code",
        "message delivery"
    ]
    is_notification_flow = any(
        kw in original_requirement.lower() for kw in notification_keywords
    )

    is_api_focus = (
        (mode == "strict" and "api" in classification.get("include_layers", []))
        or classified_type == "api"
        or is_notification_flow
    )

    kyc_domain_block = ""
    domain_guardrails = ""
    if domain == "kyc":
        kyc_domain_block = _build_kyc_domain_block(original_requirement, actor_scope)
        domain_guardrails = f"""
Domain Guardrails:
- This is a KYC / document verification domain.
- Actor scope: {actor_scope.upper()} — {"DO NOT include admin panel or backend verification steps unless explicitly mentioned." if actor_scope == "user" else "Include admin verification actions." if actor_scope == "admin" else "Include both user-facing and admin/backend flows."}
- Generate AT LEAST ONE dedicated test case per contract category mentioned (NON-RC, RC, SRC, JdPay KYC, JdPay Omni).
- Generate AT LEAST ONE test case per document status (Approved, Unapproved, Unverified, Rejected) × age condition (>2yrs, ≤2yrs) combination.
- Do NOT collapse multiple category/status combinations into a single generic test case.
- Reference the EXACT category, document type, status, and age in each test case title and steps.
"""
    elif domain == "directory_search":
        domain_guardrails = """
Domain Guardrails:
- This is a directory/search discovery application.
- Prefer scenarios around search, categories, company profiles, vertical navigation, leads/contact actions.
- Do NOT assume shopping/cart/checkout/order flows unless explicitly mentioned.
- Cross-platform flows are valid only when requirement explicitly asks transition (share/deep-link/open-in-app); otherwise keep per-platform isolation.
"""
    elif domain == "commerce":
        domain_guardrails = """
Domain Guardrails:
- This is a commerce/transaction flow.
- Include order/payment validations only when requirement supports it.
"""
    else:
        domain_guardrails = """
Domain Guardrails:
- Do not invent domain-specific flows (commerce, booking, etc.) unless requirement mentions them.
"""

    update_mode_block = _build_update_mode_block(existing_cases, update_comment, unique_domain_keys)

    e2e_block = ""
    if "e2e" in [t.lower() for t in test_types]:
        if is_api_focus:
            e2e_block = """
If test type includes 'e2e':
Generate complete API workflow validation including:
- Authentication/authorization handling
- Request/response schema validation
- Idempotency behavior
- Pagination token handling (no sort/filter steps)
- Error code mapping
- Boundary conditions
- Rate limit behavior
"""
            if is_notification_flow:
                e2e_block += """
Notification-specific validations (no UI steps):
- Provider acceptance/rejection handling
- Delivery status callbacks/webhooks
- Retry/backoff behavior
- Template/character limit enforcement
- Opt-in/opt-out compliance
- DND/time-window restrictions
"""
        elif is_session_state_flow:
            session_lines = [
                "- Perform search and open result/details page",
                "- Last searched query persistence/restoration",
                "- Last visited page persistence/restoration",
                "- Session timeout/logout behavior",
                "- Token/session invalidation after relaunch (if applicable)",
            ]
            if has_app_platform:
                session_lines.extend([
                    "- Background/foreground transition behavior on app",
                    "- App kill + relaunch behavior",
                    "- Cold start vs warm start behavior",
                    "- Offline relaunch handling (cached state) and reconnect sync",
                ])
            if has_web_platform:
                session_lines.extend([
                    "- Browser refresh/back-forward behavior with preserved context",
                    "- Session continuity after tab close/reopen and private/incognito mode checks",
                ])
            if not has_app_platform and not has_web_platform:
                session_lines.extend([
                    "- Entry/re-entry continuity on selected platform",
                    "- Session restoration after restart/reconnect",
                ])
            if is_cross_platform_handoff_flow and len(normalized_platforms) > 1:
                session_lines.append(
                    "- Cross-platform handoff continuity (source platform share/link -> target platform open -> same company/details context restored)"
                )
            e2e_block = (
                "If test type includes 'e2e':\n"
                f"Generate complete session continuity workflow validation across selected platforms ({platform_scope_text}) including:\n"
                + "\n".join(session_lines)
                + "\n"
            )
        elif domain == "directory_search":
            e2e_block = """
If test type includes 'e2e':
Generate complete search-directory workflow validation including:
- Search query + autosuggest behavior
- Category and company discovery journey
- Vertical navigation (flight, b2b, movie, pg, etc.)
- Result page relevance and pagination consistency
- Open company/details page and verify data consistency
- Profile/review-rating page transitions
- Last searched and last visited context persistence (where applicable)
- Error handling and network fluctuation behavior
"""
            if is_cross_platform_handoff_flow:
                e2e_block += """
- Cross-platform share/open flow: company details shared from web/mobile web and opened in selected app(s) with correct entity context
"""
        elif domain == "kyc":
            e2e_block = """
If test type includes 'e2e':
Generate complete KYC document reverification workflow validation including:
- User lands on KYC page → alert popup appears for aged document → user reads vintage details
- User confirms delete → document removed from UI → contract state updated
- Admin receives deletion event → verifies document removed from admin panel
- User reuploads document → new doc appears as Unverified in both user UI and admin panel
- Admin Approves/Rejects/Reverifies new doc → status reflected on user KYC page
- Contract live status re-evaluated after document replacement
- Repeat above for each contract category: NON-RC, RC, SRC, JdPay KYC, JdPay Omni
"""
        else:
            e2e_block = """
If test type includes 'e2e':
Generate complete business workflow validation including:
- Entry to completion flow validation
- Multi-step navigation checks
- Data/state consistency checks
- Session continuity and recovery behavior
- Error handling and boundary conditions
"""

    # Build analysis-extracted business rules block (from analyze_requirement output)
    business_rules = analysis_json.get("business_rules") or []
    constraints = analysis_json.get("constraints") or []
    analysis_block = ""
    if business_rules:
        rules_text = "\n".join(f"- {r}" for r in business_rules)
        analysis_block += f"\nExtracted Business Rules:\n{rules_text}\n"
    if constraints:
        constraints_text = "\n".join(f"- {c}" for c in constraints)
        analysis_block += f"\nExtracted Constraints:\n{constraints_text}\n"

    prompt = f"""
You are a Senior QA Architect with 12+ years of experience.

Requirement:
{original_requirement}

Platforms: {platforms}
Modules: {modules}
Pages: {pages}
Test Types: {test_types}

Classification:
Mode: {mode}
Type: {classified_type}
Confidence: {confidence}

{classification_guidance}
{analysis_block}
{platform_instruction_block}
{kyc_domain_block}
{update_mode_block}

Previously learned important scenarios:
{memory_patterns}

Generate REALISTIC, production-level test cases.

{e2e_block}

    Each test case must:
    - Be business realistic
    - Be detailed
    - Have minimum 6 meaningful steps
    - Keep wording concise and to the point
    - Include validation checks
    - Include varied priorities (High/Medium/Low)
    - Have specific, observable expected results (manual tester style)
    - Avoid generic expected results like "should work correctly"

IMPORTANT CONTEXT:
{context_block}
{domain_guardrails}
- Currency must be INR (₹) only when monetary validation is relevant.
- Apply GST/cancellation/booking rules only if requirement explicitly asks for those flows.

Return STRICT JSON ONLY in this structure:
{{
  "positive_tests": [],
  "negative_tests": []
}}

Return JSON only.
"""

    strict_mode = mode == "strict"

    ai_output = ask_ai(
        prompt,
        strict_mode=strict_mode,
        expect_json=True
    )

    cleaned = ai_output.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            raise ValueError("AI did not return dict")

        # 🔥 INTEGRITY ENFORCEMENT LAYER (RCA FIX)
        enforced = _enforce_testcase_integrity(parsed)
        sanitized = _sanitize_generated_cases(
            enforced,
            existing_cases=existing_cases,
            requirement=requirement,
        )
        final_output = _enforce_testcase_integrity(sanitized)

        store_patterns(requirement, final_output)

        print("RAW AI OUTPUT:")
        print(ai_output)

        return final_output

    except Exception:
        fallback = _fallback_basic_cases(requirement)
        store_patterns(requirement, fallback)
        print("JSON PARSE FAILED — USING FALLBACK")
        return fallback


# ======================================================
# 🔥 INTEGRITY ENFORCEMENT LAYER (RCA FIX)
# ======================================================

def _enforce_testcase_integrity(testcases: dict) -> dict:

    positive = testcases.get("positive_tests", [])
    negative = testcases.get("negative_tests", [])

    sequential_counter = 1

    for case_type, cases in [("positive", positive), ("negative", negative)]:
        for case in cases:

            # 1️⃣ Sequential Testcase ID
            if not case.get("testcase_id"):
                case["testcase_id"] = f"TC_{str(sequential_counter).zfill(4)}"
                sequential_counter += 1

            # 2️⃣ Mandatory Scenario
            scenario_value = case.get("scenario") or case.get("title")
            if scenario_value and str(scenario_value).strip():
                case["scenario"] = str(scenario_value).strip()
            else:
                case["scenario"] = "Validate system behavior"

            # 3️⃣ Mandatory Steps
            steps = case.get("steps", [])
            if not isinstance(steps, list) or len(steps) < 3:
                case["steps"] = [
                    "Navigate to relevant page",
                    "Perform intended action",
                    "Validate system response"
                ]

            # 4️⃣ Priority normalization
            priority = case.get("priority", "").strip().lower()
            if priority not in ["high", "medium", "low"]:
                case["priority"] = "Medium"

            # 5️⃣ Expected Result derivation
            expected_result = case.get("expected_result")
            if _is_generic_expected_result(expected_result):
                case["expected_result"] = _build_manual_expected_result(
                    scenario=case.get("scenario", ""),
                    steps=case.get("steps", []),
                    case_type=case_type
                )

    return {
        "positive_tests": positive,
        "negative_tests": negative
    }


def _is_generic_expected_result(expected_result) -> bool:
    if not expected_result or not str(expected_result).strip():
        return True

    normalized = str(expected_result).strip().lower()
    generic_markers = [
        "should work correctly",
        "works correctly",
        "should work as expected",
        "works as expected",
        "system behaves as expected",
        "expected behavior",
        "system should successfully complete"
    ]
    return any(marker in normalized for marker in generic_markers)


def _build_manual_expected_result(scenario: str, steps: list, case_type: str) -> str:
    objective = _normalize_objective(scenario)
    channel = _infer_test_channel(scenario, steps)
    validation_evidence = _extract_validation_evidence(steps)

    if case_type == "negative":
        return (
            f"System blocks invalid/unauthorized action for {objective}; "
            f"{validation_evidence}; no unintended data/state change occurs."
        )

    if channel == "api":
        return (
            f"{objective} is completed successfully; API returns expected status "
            f"code with valid response contract; {validation_evidence}; data is "
            f"retrievable in subsequent verification call."
        )

    return (
        f"{objective} is completed successfully; {validation_evidence}; "
        f"success state is visible to user and data remains consistent after refresh."
    )


def _normalize_objective(scenario: str) -> str:
    if not scenario or not str(scenario).strip():
        return "the intended workflow"

    cleaned = str(scenario).strip().rstrip(".")
    prefixes = ["validate ", "verify ", "check ", "ensure ", "confirm ", "test "]

    lower_cleaned = cleaned.lower()
    for prefix in prefixes:
        if lower_cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    return cleaned if cleaned else "the intended workflow"


def _infer_test_channel(scenario: str, steps: list) -> str:
    combined = f"{scenario} {' '.join(steps or [])}".lower()
    api_keywords = [
        "api",
        "endpoint",
        "request",
        "response",
        "status code",
        "payload",
        "token",
        "http",
        "webhook"
    ]
    return "api" if any(keyword in combined for keyword in api_keywords) else "ui"


def _extract_validation_evidence(steps: list) -> str:
    if not isinstance(steps, list) or not steps:
        return "all validation checkpoints pass as per requirement"

    verification_keywords = [
        "verify",
        "validate",
        "confirm",
        "check",
        "ensure",
        "assert",
        "observe"
    ]

    for step in reversed(steps):
        if not isinstance(step, str):
            continue
        if any(keyword in step.lower() for keyword in verification_keywords):
            trimmed_step = step.strip().rstrip(".")
            if len(trimmed_step) > 140:
                trimmed_step = f"{trimmed_step[:137]}..."
            return f"validation evidence captured in step: {trimmed_step}"

    final_step = str(steps[-1]).strip().rstrip(".")
    if len(final_step) > 140:
        final_step = f"{final_step[:137]}..."
    return f"final execution check confirms: {final_step}"


# ======================================================
# Fallback
# ======================================================

def _fallback_basic_cases(requirement):
    return {
        "positive_tests": [
            {
                "testcase_id": f"TC_{uuid.uuid4().hex[:6].upper()}",
                "priority": "Medium",
                "scenario": f"Validate {requirement}",
                "steps": [
                    "Navigate to relevant page",
                    "Perform required action",
                    "Verify outcome"
                ],
                "expected_result": _build_manual_expected_result(
                    scenario=f"Validate {requirement}",
                    steps=[
                        "Navigate to relevant page",
                        "Perform required action",
                        "Verify outcome"
                    ],
                    case_type="positive"
                )
            }
        ],
        "negative_tests": []
    }
