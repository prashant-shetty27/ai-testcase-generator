def build_complete_prompt(
    requirement,
    platforms,
    modules,
    pages,
    test_types,
    memory_patterns,
    context_block,
    classification=None
):

    classification_guidance = ""
    dynamic_generation_rules = ""

    has_memory = bool(memory_patterns and len(str(memory_patterns).strip()) > 5)

    classified_type = "unknown"
    confidence = 0

    if classification:
        classified_type = classification.get("type", "unknown")
        confidence = classification.get("confidence", 0)

    # ----------------------------------------
    # CONFIDENCE-BASED GENERATION STRATEGY
    # ----------------------------------------

    if not has_memory:
        # First-time requirement
        dynamic_generation_rules = """
Generate:
- Minimum 8 positive cases
- Minimum 6 negative cases
- Minimum 3 High priority cases
- Minimum 2 boundary cases
- Minimum 2 integration scenarios
"""
    else:
        confidence_buckets = [
            (
                confidence < 0.4,
                """
Classification confidence is LOW.
Expand coverage broadly across:
- UI
- API
- Validation
- Security
- Performance
Add exploratory edge cases.
Increase diversity over depth.
"""
            ),
            (
                0.4 <= confidence < 0.7,
                """
Classification confidence is MEDIUM.
Generate balanced coverage:
- Expand boundary scenarios
- Add integration flows
- Increase negative path depth
Avoid duplication of prior scenarios.
"""
            ),
            (
                0.7 <= confidence < 0.9,
                """
Classification confidence is HIGH.
Focus on:
- Deep edge cases
- Risk-heavy areas
- Cross-layer interactions
- Complex negative scenarios
Add advanced validations.
"""
            ),
            (
                confidence >= 0.9,
                """
Classification confidence is VERY HIGH.
Generate precision-focused scenarios:
- Rare edge cases
- Concurrency risks
- Data consistency anomalies
- Failure injection cases
- Advanced stress conditions
Ensure no repetition of previous patterns.
"""
            ),
        ]

        dynamic_generation_rules = next(
            rules for condition, rules in confidence_buckets if condition
        )

    return f"""
You are a Senior QA Architect with strong experience in Indian SaaS platforms.

Requirement:
{requirement}

Application Context:
- Operates only in India
- Currency: INR
- Follow realistic business logic

Platform Selection:
{platforms}

Module Selection:
{modules}

Page Selection:
{pages}

Test Types Requested:
{test_types}

Platform / Module / Page Considerations:
{context_block}

Previously Learned Critical Scenarios:
{memory_patterns}

System Classification:
Type: {classified_type}
Confidence: {confidence}

Instructions:
1. Identify complete business flows.
2. Identify revenue impact areas.
3. Identify integration risks.
4. Identify boundary values.
5. Identify negative paths.
6. Identify data consistency risks.
7. If the requirement lists CATEGORY-WISE rules or numbered conditions, generate AT LEAST ONE dedicated test case per category and per condition combination. Do NOT collapse multiple rules into a single generic test case.
8. If the requirement mentions specific statuses (e.g., Approved, Unverified, Unapproved, Active, Inactive), generate separate test cases for EACH status variant.
9. If alert/warning popups are mentioned, include tests for: popup display, popup content accuracy (vintage date shown), popup dismiss, and post-action state.
10. If delete actions are mentioned, test: delete confirmation, UI refresh after delete, undo/re-upload prevention, and impact on associated contract state.
11. If the requirement mentions a "type" field (e.g., vehicle type, category type, listing type, document type, contract type), generate AT LEAST ONE dedicated test case per type variant. Label each variant scenario with `@TypeName` in the scenario title (e.g., `@Car`, `@Bike`, `@Truck`, `@Platinum`, `@PaidExpired`). Do NOT collapse all type variants into a single generic test case. Contract types include: Paid-Platinum, Paid-Diamond, Paid-Normal, Paid-NationalListing, Paid-Other, NonPaid, PaidExpired — each needs its own test case.
12. For mobile web test cases: target browsers are Chrome + Samsung Internet on Android, and Safari + Chrome on iOS. Do NOT generate Firefox Mobile test cases for mobile web. This is a mobile touch website — do not include native app lifecycle steps (background/foreground, push notifications).
13. If the requirement is related to any of the following search intents — category search, company search, product search, service search, business search, or movies search — ALWAYS include location-aware test cases:
    a. One test case where user location is auto-detected via GPS and results are verified to match that city/area.
    b. One test case where user manually changes location mid-session and results refresh to the new location.
    c. One test case where location permission is DENIED — verify graceful fallback to manual city selection (no crash, no empty screen).
    d. One test case for hyperlocal/proximity search (area or pincode level) — results ranked by proximity to user.
    e. One test case for a boundary-city scenario (e.g., Mumbai/Thane, Delhi/Gurgaon, Bengaluru/Whitefield) — results must not bleed across city boundaries.
    Label each location case with `@Location` in the scenario title (e.g., `@Location GPS auto-detect`, `@Location Permission Denied`, `@Location City Change`).
    These location cases are IN ADDITION to all other required test cases — do NOT replace existing scenarios with location ones.
14. If the requirement is related to call numbers, phone display, VN, DVN, Actual number, Preferred number, or "Show Number" behavior — generate SEPARATE test cases per number type. Use `@VN`, `@DVN`, `@Actual`, `@Preferred` labels in the scenario title. Apply these mandatory rules per type:
    @VN — WEB: number shown inline (no button). TOUCH/APP: "Show Number" button reveals single mobile-type number. VN is ONLY for paid clients — verify blocked for non-paid.
    @DVN — Number shown but MUST change after: (a) cache clear, (b) session expiry, (c) ~1-minute TTL. Generate one test case per rotation trigger. DVN is ONLY for non-paid — verify blocked for paid clients.
    @Actual — "Show Number" button on all platforms. May reveal single OR multiple numbers (mobile/landline/tollfree). Test both single and multi-number variants. Emergency/helpline Actual numbers must display regardless of contract status.
    @Preferred — Sourced from Google; behaves identically to Actual for display and routing. Must not be misclassified as VN or DVN.
    Cross-cutting for ALL types: number must be masked/hidden before reveal (not in DOM or network response); every reveal must fire a lead event; Paid Expired contract must deactivate VN; non-paid → paid upgrade must replace DVN with VN.
15. SEARCH RESULT PAGE vs DETAILS PAGE routing — strictly enforce this in ALL test cases:
    RESULT PAGE: Category search (autosuggest OR freetext) ALWAYS lands on Result Page. Generate listing-level test cases: filters, sorting, count accuracy, vehicle type section below city, pagination, no-result state, back navigation restoring scroll+filters.
    DETAILS PAGE: Company/brand name direct search ALWAYS lands on Details Page. Generate company profile test cases: contact data, address, ratings, claimed/unclaimed badge, branch selection.
    COMPANY RESULT PAGE (exception): Company freetext OR outlet-grouped search (e.g. "Pizza Hut", "McDonald's outlets") lands on a Company Result Page showing multiple outlet listings — generate outlet-listing test cases here, NOT company profile test cases.
    For B2B requirements: if the page is a B2B result page (PRP), ALL test cases must be category-search-based. DO NOT generate company profile, company name search, or Details Page test cases for a B2B result page requirement. Vehicle type display below city is a mandatory test area for every B2B result page requirement.

{dynamic_generation_rules}

16. B2B and B2C are SEARCH TYPES — the search query determines whether a search is B2B or B2C, and businesses/contracts in results are automatically classified accordingly. A user is always just a user. STRICTLY FORBIDDEN phrases in any test step: "B2B user", "B2C user", "authorized B2B user", "B2B credentials", "B2B login", "B2B account". These do not exist.
    Login steps must be context-driven — ask yourself: does this flow REQUIRE the user to be logged in?
    - PUBLIC flows (NO login step): category search, result page browsing, details page viewing, vehicle directory browsing, B2B/B2C search directories. Start directly from opening the URL.
    - AUTHENTICATED flows (login step allowed): dashboards, leads, saved searches, account settings, profile management, RFQ submission, paid features, contract management, wishlists, personalised recommendations.
    - If login IS needed, write ONLY: "Login with valid credentials" or "Login as a registered user". Never attach B2B/B2C/role labels to the login step.

Each test case must:
- Have 6–8 meaningful steps
- Include validation logic
- Be business realistic
- Avoid generic statements
- Reference the EXACT category/rule/condition from the requirement (e.g., "RC - Address Proof >2 years, Approved, live contract")

Return STRICT JSON only:

{{
  "positive_tests": [],
  "negative_tests": []
}}
"""