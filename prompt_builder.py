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

═══════════════════════════════════════════
PHASE 1 — ANALYSE BEFORE YOU GENERATE
═══════════════════════════════════════════
Before writing any test case, read the requirement fully and identify:
A. Complete end-to-end business flows involved.
B. Revenue-impacting paths (payments, contracts, leads, upgrades).
C. Integration touchpoints (API calls, third-party systems, data sync).
D. Boundary values (min/max, thresholds, limits explicitly stated).
E. Negative paths (invalid input, blocked access, error states).
F. Data consistency risks (state changes, concurrent actions, rollback).
G. PRIMARY TEST SUBJECT vs REFERENCE TERMS — this is critical:
   - PRIMARY TEST SUBJECT: the feature, behaviour, or element the requirement is actually asking you to test.
   - REFERENCE TERM: a word or element used to describe position, condition, or context — NOT the thing being tested.
   - A requirement can have MULTIPLE reference terms simultaneously — identify ALL of them before writing steps.
   Examples:
     "vehicle type section BELOW CITY" → PRIMARY = vehicle type section behaviour | REFERENCE = city (positional anchor only)
     "listing WITH APPROVED CONTRACT" → PRIMARY = listing behaviour | REFERENCE = Approved contract (condition/filter)
     "search results FOR MUMBAI" → PRIMARY = search result behaviour | REFERENCE = Mumbai (geographic filter)
     "Show VN FOR PAID CLIENT on RESULT PAGE in MUMBAI" → PRIMARY = VN display behaviour | REFERENCES = paid client (eligibility condition), result page (context), Mumbai (location filter) — none of these three are the test subject
   Rule: Reference terms set up the scenario context. They must NOT become the focus of test steps. Use ALL reference terms as setup/condition context only — validate the primary test subject in every verification step.
Only after this analysis, proceed to generate test cases.

═══════════════════════════════════════════
PHASE 2 — COVERAGE RULES (apply conditionally)
═══════════════════════════════════════════
Apply each rule ONLY when the condition is true for this requirement:

RULE A — Category-wise conditions:
If the requirement lists CATEGORY-WISE rules or numbered conditions, generate AT LEAST ONE dedicated test case per category and per condition combination. Do NOT collapse multiple rules into a single generic test case.

RULE B — Status variants:
If the requirement mentions specific statuses (e.g., Approved, Unverified, Unapproved, Active, Inactive), generate a separate test case for EACH status variant.

RULE C — Popup / alert actions:
If alert or warning popups are mentioned, cover: popup display trigger, popup content accuracy, popup dismiss, and post-action state verification.

RULE D — Delete actions:
If delete is mentioned, cover: delete confirmation dialog, UI refresh after delete, prevention of undo/re-upload, and impact on any associated contract or record state.

RULE E — Type fields:
If the requirement explicitly names type variants (e.g., vehicle type, document type, contract type), generate AT LEAST ONE dedicated test case per named type. Label each with `@TypeName` in the scenario title. Do NOT collapse variants. Do NOT generate type-variant test cases if the requirement does not name specific types — use the generic term only.
  Contract types (use ONLY if the requirement mentions contracts): Paid-Platinum, Paid-Diamond, Paid-Normal, Paid-NationalListing, Paid-Other, NonPaid, PaidExpired.

RULE F — Platform-specific browser scope:
  Web (desktop): test on Chrome and Safari. Do NOT assume Firefox or Edge unless the requirement explicitly names them.
  Touch/mobile web: valid browsers are Chrome and Samsung Internet on Android; Safari and Chrome on iOS. Do NOT generate Firefox Mobile cases.
  Android app / iOS app: native app — no browser mentioned in steps unless the requirement is about in-app browser behaviour.
  Do NOT include native app lifecycle steps (background/foreground, push notifications) for mobile web touch platform.

RULE G — Location-aware cases (search with geographic relevance):
Apply ONLY when ALL of the following are true:
  1. The requirement involves search results (category search, product search, service search, movies search).
  2. The requirement explicitly mentions city, area, location, pincode, geo-filtering, or city-switching as part of the CORE TESTED BEHAVIOUR — not just as a display label or positional anchor.
  3. The requirement is NOT purely about UI layout, styling, label formatting, or element positioning — if city only appears as a reference anchor (e.g., "below city name"), skip location cases.
  Add these ADDITIONAL test cases (labelled `@Location` in scenario title):
  - `@Location GPS Auto-detect`: location auto-detected via GPS, results and city name match detected city.
  - `@Location City Change`: user manually changes city mid-session, results and vehicle type section refresh to new city.
  - `@Location Permission Denied`: GPS permission denied, platform falls back to manual city selection without crash or blank screen.
  - `@Location Hyperlocal`: search by area or pincode, results ranked by proximity to user.
  - `@Location Boundary City`: search near a city boundary (e.g., Mumbai/Thane), results do not bleed across boundary.
  These are IN ADDITION to all other required cases — do NOT replace existing cases with location ones.

RULE H — Call number types (VN / DVN / Actual / Preferred):
Apply ONLY when the requirement explicitly mentions call numbers, phone display, VN, DVN, Actual, Preferred, or "Show Number" behaviour.
  Generate SEPARATE test cases per number type, labelled `@VN`, `@DVN`, `@Actual`, `@Preferred`:
  @VN: WEB — number shown inline, no button. TOUCH/APP — "Show Number" button, single mobile number. VN is for paid clients only — verify it is blocked for non-paid.
  @DVN: Number rotates after (a) cache clear, (b) session expiry, (c) ~1-minute TTL — one test case per trigger. DVN is for non-paid only — verify blocked for paid clients.
  @Actual: "Show Number" button on all platforms. Test single-number and multi-number (mobile/landline/tollfree) variants. Helpline/emergency numbers display regardless of contract status.
  @Preferred: Google-sourced number. Display and routing identical to Actual. Must not be misclassified as VN or DVN.
  Cross-cutting (ALL types): number hidden before reveal (not in DOM or network); every reveal fires a lead event.
  Generate SEPARATE test cases for these state transitions:
    - Paid Expired contract → VN must deactivate (number no longer shown inline or via button).
    - Non-paid → paid upgrade → DVN must be replaced by VN (verify old DVN is removed).

RULE I — Search routing (enforced in all search-related test cases only — skip for non-search requirements like KYC, payments, profile):
  Category search (autosuggest OR freetext) → ALWAYS lands on Result Page.
    Result Page test areas: filters, sorting, listing count, vehicle type section below city, pagination, no-result state, back navigation restoring scroll and filters.
  Company/brand name direct search → ALWAYS lands on Details Page.
    Details Page test areas: contact data, address, ratings, claimed/unclaimed badge, branch selection.
  Company freetext OR outlet-grouped search (e.g. "Pizza Hut outlets") → lands on Company Result Page.
    Company Result Page test areas: outlet listings, not company profile.
  B2B Result Page (PRP): ALL test cases must be category-search-based. DO NOT generate company profile, company name search, or Details Page test cases for a B2B PRP requirement. Vehicle type display below city is mandatory.

═══════════════════════════════════════════
PHASE 3 — TERMINOLOGY AND FORBIDDEN PATTERNS
═══════════════════════════════════════════
FORBIDDEN — never use these in any test step or title:
  "B2B user" | "B2C user" | "authorized B2B user" | "B2B credentials" | "B2B login" | "B2B account" | "directory" | "B2B directory" | "search directory"

B2B and B2C are SEARCH TYPES — the search query classifies the intent, and businesses/results are automatically classified accordingly. A user is always just a user.

LOGIN — include a login step only when the flow genuinely requires authentication:
  Requires login: dashboards, leads, saved searches, account settings, profile, RFQ submission, paid features, contract management.
  Does NOT require login: category search, result page browsing, details page viewing, B2B/B2C search platforms — start directly from opening the URL.
  When login IS needed: write "Login with valid credentials" or "Login as a registered user" — no role labels ever.

DOMAIN TERMS — never invent or assume examples unless the requirement explicitly names them.
  "Vehicle type", "category", "product type", "service type" are context-specific — do not assume values like "Car, Truck, Bike" unless those exact values appear in the requirement.

═══════════════════════════════════════════
PHASE 4 — STEP WRITING RULES
═══════════════════════════════════════════
Test case TITLE — must be scenario-specific, never generic:
  - Title must include: WHAT is being tested + the KEY CONDITION + direction (pass/fail/boundary).
    BAD: "Positive test for vehicle type" | "Test case 1" | "Verify listing page"
    GOOD: "Vehicle type section renders and filters correctly after category search on B2B result page — positive"
    GOOD: "Vehicle type section absent for city with no associated types — empty state handling"
  - Do NOT reuse the same title structure across multiple test cases. Each title must be unique and self-describing.

Every step must earn its place:
  - Each step = one purposeful action + its expected outcome in the same sentence.
    BAD: "Navigate to the results page."
    GOOD: "Navigate to the results page and verify listings load with correct filters applied."
  - Steps must build on each other — each step advances the scenario forward.
  - FORBIDDEN step patterns (these add zero value, remove them):
    "Observe the UI" | "Check the page" | "Verify the screen loads" | "Ensure the app is open" | "Wait for the page to load" | "Open the app"

Step structure — reference terms vs primary test subject:
  - Use the PRIMARY TEST SUBJECT (identified in Phase 1G) as the focus of every step's verification.
  - Reference terms (city, contract status, document type used as context) appear only in setup steps or as condition context — never as the primary thing being verified.
  - Step flow must be: [setup/navigate using reference context] → [act on primary subject] → [verify primary subject behaviour].
    WRONG: "Verify city name is displayed at top of page. Verify vehicle type section is below city."
      (city is a reference — its display is not the test. Vehicle type is the subject.)
    RIGHT: "Scroll to the section below the city name and verify the vehicle type section is present, correctly positioned, and fully rendered with no overlap."
      (city used as positional anchor; vehicle type section is what is actually verified)

Browser and device — mention only when it directly affects the test outcome:
  - Mention ONCE at step 1 when testing: screen layout, touch behaviour, browser-specific rendering, platform-specific gestures (Safari swipe, Android back button).
  - If the test logic is platform-agnostic, do NOT mention any device or browser.
  - Never list multiple browsers as examples in a step — "(e.g., Chrome, Samsung Internet)" belongs in a dedicated browser-comparison test case only.

No data leakage or assumption:
  - Do NOT reference internal API field names, backend config values, database terms, or system IDs unless they appear verbatim in the requirement.
  - Do NOT assume data values (counts, thresholds, prices, phone numbers, URLs) not stated in the requirement.
  - Do NOT introduce business logic beyond what the requirement describes — test the literal requirement, not your interpretation of it.

{dynamic_generation_rules}

Each test case must:
- Have 5–8 steps — scale to the scenario complexity. Simple validations need 5 focused steps. Complex flows may use up to 8. NEVER pad steps to reach a count — every step must add value.
- Have a unique, self-describing title (see Phase 4 title rule above)
- Cover the exact scenario described — no filler, no assumed data, no invented role labels
- If the requirement has explicit conditions/rules, reference them exactly in the relevant step (e.g., "RC - Address Proof >2 years, Approved, live contract"). If no explicit condition exists, describe the scenario state clearly without fabricating conditions.
- Be business-realistic and self-contained

Return STRICT JSON only:

{{
  "positive_tests": [],
  "negative_tests": []
}}
"""