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

╔══════════════════════════════════════════════════════════════╗
║   CRITICAL HARD RULES — READ BEFORE ANYTHING ELSE           ║
║   These OVERRIDE every other instruction. No exceptions.     ║
╚══════════════════════════════════════════════════════════════╝

BANNED WORDS — If any of these appear anywhere in your output, DELETE them before returning:
  • "directory" / "B2B directory" / "search directory" → NEVER use. There is no directory.
  • "B2B user" / "B2C user" / "authorized B2B user" / "B2B credentials" / "B2B login" / "B2B account" → NEVER use. A user is just a user.
  • "B2B search page" / "B2B search platform" / "B2B platform" / "B2B homepage" / "B2B URL" → NEVER use. B2B is a SEARCH TYPE, not a page. There is no B2B page — there is only the platform.
  • Inches or pixels for device size: "6.1-inch" / "6.7-inch" / "1080x2400" / "375px" → NEVER use. Use ONLY: "compact phone", "standard phone", "large phone", "tablet".

BANNED STEP PATTERNS — Delete any step matching these patterns:
  • "Observe the UI" | "Check the page" | "Verify the screen loads" | "Ensure the app is open" | "Wait for the page to load" → Filler. Remove.
  • Any step that verifies city name, location name, or area name as the PRIMARY thing being checked → Wrong focus. City/location are reference anchors, not test subjects.
  • Any step that introduces data (city names, vehicle types, prices, counts, company names) not explicitly stated in the requirement → Data leakage. Remove.

MANDATORY — Before returning JSON:
  • EVERY step must be directly relevant to the PRIMARY TEST SUBJECT identified in Phase 1G.
  • For any frontend requirement: ALL 4 @Lang cases MUST be present (@Lang Regional Script, @Lang Bilingual, @Lang Mixed Script, @Lang Input Search). Non-negotiable.
  • Browser mention: MAXIMUM ONCE, only at step 1, only when layout/rendering is being tested.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

RULE F — Platform-specific browser and device scope:
  Web (desktop): test on Chrome and Safari. Do NOT assume Firefox or Edge unless the requirement explicitly names them.
  Touch/mobile web: valid browsers are Chrome and Samsung Internet on Android; Safari and Chrome on iOS. Do NOT generate Firefox Mobile cases.
  Android app / iOS app: native app — no browser mentioned in steps unless the requirement is about in-app browser behaviour.
  Do NOT include native app lifecycle steps (background/foreground, push notifications) for mobile web touch platform.
  Device size terminology — NEVER use inches (e.g., 6.1-inch, 6.7-inch) or pixel resolutions (e.g., 1080x2400) in any test step. Use ONLY these plain terms:
    "compact phone" — small screen, one-hand use (think budget/SE-size phones)
    "standard phone" — everyday mid-size phone (most common)
    "large phone" — bigger display, two-hand use (Pro Max / Ultra class)
    "tablet" — iPad or Android tablet form factor
  Mention device size ONLY when the test is specifically about layout behaviour on that screen size. For all other tests, do not mention any size.

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

RULE J — Multilingual / Regional Language cases (India context):
  ORDERING: @Lang cases are ALWAYS generated LAST — after all primary positive, boundary, and negative cases. Never test case #1, #2, or #3.

  @Lang is MANDATORY only for consumer-facing UI features where content rendering is the primary concern:
    ✓ Search results pages, listing pages (PRP/PDP/catalogue), movie listings, product/category browsing
    ✓ Any feature where listings, names, prices, counts, dates, or error messages are displayed to a consumer user
    ✓ Features that explicitly involve language selection, regional script display, or multilingual content

  @Lang is OPTIONAL (generate only if directly relevant) for:
    - Admin dashboards, leads sections, CRM tools, ops/internal panels — these are operator-facing, not consumer-facing; language rendering is rarely the concern
    - Sync flows, permission flows, campaign flows, settings — generate @Lang only if the requirement explicitly mentions language or regional script support
    - Forms and data entry screens — generate @Lang Input Search only if the form accepts user-typed search or regional input

  @Lang is SKIPPED entirely when:
    - The requirement is strictly backend / API / database with zero user-facing rendering
    - The requirement explicitly states English-only scope
    - The feature is a backend admin action (approve, reject, delete, update status) with no content display

  When @Lang IS generated, each case must test a DISTINCTLY DIFFERENT scenario — no near-duplicates:
  - `@Lang Regional Script`: verify content (listings, labels, error messages) renders correctly in regional script — no garbling or encoding errors. USE ONLY when the feature displays content to users.
  - `@Lang Bilingual`: verify English + regional text coexist on screen without overlap or truncation. USE ONLY when the feature shows mixed-language content simultaneously.
  - `@Lang Mixed Script`: verify a field accepts and stores mixed English + regional script input. USE ONLY when the feature has a text input where users type.
  - `@Lang Input Search`: verify regional script input triggers correct results. USE ONLY when the feature has a search or query input.

  If fewer than 4 of the above scenarios are genuinely applicable to the feature — generate only those that apply. DO NOT generate @Lang cases just to fill a quota.

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
RULE K — PRIORITY ASSIGNMENT (apply to every test case)
═══════════════════════════════════════════
Assign priority based on business impact — do NOT default every case to Medium.

  HIGH — assign when:
    • Core business flow: unlock/purchase/payment/credit deduction, lead access, wallet transactions
    • Revenue-impacting path: any action that charges the user, deducts credits, or controls access to paid features
    • Data integrity or concurrency risk: concurrent actions, race conditions, duplicate writes, rollback failures
    • Critical auth/security: session expiry mid-transaction, unauthorised access to locked data
    • Hard business rule enforcement: daily limit reached, eligibility checks, access control

  MEDIUM — assign when:
    • Standard functional display: list rendering, card fields, filter/sort behaviour, navigation
    • Boundary conditions on functional flows: limit thresholds, empty states, count boundaries
    • Standard negative cases: error message display, blocked actions with clear feedback
    • Integration flows: cross-module state updates, state propagation between screens

  LOW — assign when (these are supplementary, always generated LAST):
    • Accessibility: keyboard-only navigation, screen reader labels, tab order, contrast
    • Browser rendering / visual consistency: zoom levels, layout at different viewpoints, cross-browser pixel checks
    • Incognito / private browsing mode
    • Network-level security checks: verifying data is masked in DevTools/network inspector (not the feature itself)
    • Session continuity across non-transactional events: tab close/reopen with no pending transaction
    • Performance or SLA assertions embedded in functional flows

═══════════════════════════════════════════
RULE L — TEST CASE ORDERING (enforce across all generated cases)
═══════════════════════════════════════════
Generated test cases MUST be ordered in this sequence — never mix tiers:

  1. HIGH priority cases first — core flows, revenue paths, concurrency/data risks
  2. MEDIUM priority cases — functional display, boundary, standard negatives, integrations
  3. LOW priority cases last — accessibility, rendering, incognito, network masking, zoom
  4. @Lang cases absolutely last (after all Low priority cases)

  NEVER place a Low priority case before any Medium or High priority case.
  NEVER place accessibility or browser-rendering cases in the first half of the output.

═══════════════════════════════════════════
PHASE 4 — STEP WRITING RULES
═══════════════════════════════════════════
Test case TITLE — must be scenario-specific, never generic:
  - Title must include: WHAT is being tested + the KEY CONDITION + direction (pass/fail/boundary).
    BAD: "Positive test for vehicle type" | "Test case 1" | "Verify listing page"
    GOOD: "Vehicle type section renders and filters correctly after category search on B2B result page — positive"
    GOOD: "Vehicle type section absent for city with no associated types — empty state handling"
  - Do NOT reuse the same title structure across multiple test cases. Each title must be unique and self-describing.

Step 1 — Navigation (how to write the starting step correctly):
  - Search/browse flows (no login needed): Use the platform name when it is known — do NOT say "platform URL" if the platform is clear from context.
    • web → "Open the website and perform [category] search"
    • touch → "Open the mobile site and perform [category] search"
    • android app → "Open the Android app and perform [category] search"
    • ios app → "Open the iOS app and perform [category] search"
    • platform unknown → "Open the platform URL and perform [category] search"
    NEVER say "Open the B2B homepage", "Navigate to the B2B search page", "Open the B2B platform" — B2B is a search TYPE, not a page.
  - Authenticated flows (dashboards, leads, contracts, profile): Start with "Login with valid credentials and navigate to [specific section]".
  - NEVER say "Open the B2B directory", "Open the B2B homepage", "Open the B2B search platform" — there is no B2B-specific page.

Every step must earn its place:
  - Each step = one purposeful action + its expected outcome in the same sentence. Keep it short and direct — ideally under 20 words. No filler preamble.
    BAD: "Navigate to the results page."
    GOOD: "Search for the vehicle category and verify listings load with correct filters applied."
  - Write in active voice. Cut any word that doesn't add meaning.
    BAD: "It should be verified that the results are displayed correctly on the screen."
    GOOD: "Verify results display correctly with title, price, and rating visible."
  - Steps must build on each other — each step advances the scenario forward.
  - Every step must be DIRECTLY relevant to the PRIMARY TEST SUBJECT. If a step tests something outside the requirement scope (unrelated UI, keyboard navigation not asked for, unrelated autosuggest behaviour), DELETE IT.
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

  EXCEPTION — city IS a valid primary test subject when the feature is location-aware or city-context-driven:
    - "Verify that results/listings displayed are relevant to the selected city" → VALID (city filtering is the feature)
    - "Change the city and verify results update to reflect the new city" → VALID (city switching is the feature)
    - "Verify movie hotkey listings are city-specific" → VALID (location context drives results)
    - "Verify city name text appears at the top" alone → INVALID (display check only, not functional)

Browser and device — mention only when it directly affects the test outcome:
  - Mention ONCE at step 1 when testing: screen layout, touch behaviour, browser-specific rendering, platform-specific gestures (Safari swipe, Android back button).
  - If the test logic is platform-agnostic, do NOT mention any device or browser.
  - Never list multiple browsers as examples in a step — "(e.g., Chrome, Samsung Internet)" belongs in a dedicated browser-comparison test case only.
  - Device size: use ONLY "compact phone", "standard phone", "large phone", or "tablet" — NEVER use inches or pixel resolution. Mention size only when layout is being tested.

Cross-cutting concerns (logging, compliance, analytics, audit):
  - NEVER append logging/compliance/audit as a final step to a functional test case. These are separate test cases.
  - If the requirement mentions logging or compliance, write EXACTLY ONE dedicated test case for it — do not repeat it as a tail step across multiple test cases.
  - Wrong: Step 7 of a search test = "Ensure all interactions are logged for compliance."
  - Right: A standalone test case titled "Chatbot interaction log recorded correctly for compliance — positive"

Page scope — do not assume a single page:
  - If the requirement does NOT name a specific page, do NOT lock all test cases to one page (e.g. "company details page only").
  - If the feature exists on multiple pages (e.g. Show Number on result page, PRP, PDP, catalogue, details page), spread coverage across all applicable pages or reference "all pages where [feature] is present" generically.
  - Only restrict to one page when the requirement explicitly names it.

Count-based display — universal rule for any feature that shows a list of items (numbers, images, reviews, results, tags, filters, documents):
  - 0 items → empty state: correct message shown, no broken layout
  - Exactly 1 item → displayed inline or as a single entry, no list/panel/carousel needed
  - 2–few items → list or panel renders correctly, all items visible without scroll
  - Many items (beyond viewport) → scrollable container; verify all items are reachable via scroll
  - Item ordering → first item is primary/most relevant; order is consistent on re-load
  Apply this pattern to any feature where the count of displayed items can vary.

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

BEFORE RETURNING OUTPUT — MANDATORY SELF-CHECK (2-pass gate — run both before returning):

━━━━━━━━━━━━━━━━━━━━━━━━━━
PASS 1 — REMOVE VIOLATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━

  BANNED WORDS:
  ✗ "directory" / "B2B directory" / "search directory" → DELETE. No substitute.
  ✗ "B2B user" / "B2C user" / "B2B credentials" / "B2B login" → DELETE. Say "user" only.
    e.g. ✗ "Verify B2B user sees PRP" → ✓ "Verify user sees PRP"
  ✗ "B2B page" / "B2B homepage" / "B2B platform" / "B2B URL" → DELETE. B2B is a search TYPE, not a page.
    e.g. ✗ "Open B2B homepage" → ✓ "Open the mobile site and perform B2B search" (touch) / "Open the website and perform B2B search" (web) / "Open the platform URL and perform B2B search" (platform unknown)
  ✗ Inch/pixel sizes ("6.1-inch", "375px", "1080x2400") → DELETE. Use "compact phone", "standard phone", "large phone", "tablet" — or drop size if layout isn't being tested.
  ✗ Pixel tap sizes ("44x44px", "48dp") → DELETE. Use qualitative language.
    e.g. ✗ "tap targets are at least 44x44px" → ✓ "vehicle type options are clearly tappable without mis-taps"

  STEP QUALITY:
  ✗ Filler steps ("Observe the UI", "Check the page", "Verify screen loads", "Wait for page to load", "Navigate to relevant page", "Perform intended action") → DELETE. Rewrite as a specific action + expected outcome tied to this requirement.
    e.g. ✗ "Verify the screen loads correctly" → ✓ "Verify the Movie listing page shows posters, title, rating, and showtime for the selected city"
  ✗ Data invented from thin air — city names, vehicle types, company names, prices, counts not in the requirement → DELETE. Use generic terms.
    e.g. ✗ "Search for 'Hyundai Creta' in Mumbai" (not stated) → ✓ "Search for the target vehicle category in the selected city"
  ✗ City/location name as the SOLE purpose of a step (no functional outcome) → DELETE or rewrite.
    e.g. ✗ "Verify city name appears at the top" → ✓ "Verify movie listings displayed are specific to the selected city"
  ✗ Cross-cutting concern (logging, analytics, audit trail, compliance, session recording) as the last step of a functional test case → DELETE that step. Write it as its own standalone test case instead.
    e.g. ✗ Last step: "Verify the search action is logged in analytics" inside a Search functional TC → ✓ Separate TC: "Verify search events are captured in analytics"
  ✗ SLA/response-time assertion embedded inside a functional test case → REMOVE from the functional TC. It must be its own dedicated performance test case.
    e.g. ✗ Step 6: "Verify results load within 5 seconds" inside a functional TC → ✓ Separate TC: "Verify search results load within the specified SLA"

  AUTH / FLOW:
  ✗ Login step inside a search/browse/result flow that does not require login → REMOVE. These flows start directly from the platform.
    e.g. ✗ Step 1: "Login with valid credentials" for a PRP → ✓ Step 1: "Open the mobile site and perform the relevant category search" (touch) / "Open the website and perform the relevant category search" (web)

  BROWSER:
  ✗ Browser mentioned more than once in a test case → REMOVE extra mentions. One mention at step 1 only, exclusively for layout/rendering tests.

━━━━━━━━━━━━━━━━━━━━━━━━━━
PASS 2 — FILL COVERAGE GAPS
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Re-read your requirement. For each dimension below, ask: is it covered? If not — ADD it now.

  LOCATION / CITY (for location-aware features — city filtering, geo-specific results, location-linked content):
  ✓ Is there a test case verifying content/results update when the city is changed?
    e.g. "Verify that changing city from the header updates the movie listings shown on the page"
    → If MISSING → ADD it.
  ✓ Is there a negative case for an unserviced or invalid city?
    e.g. "Verify an appropriate message is shown when the selected city has no listings for the searched category"
    → If MISSING → ADD it.

  @LANG (frontend/UI requirements — mandatory):
  ✓ Are ALL 4 @Lang cases present: Regional Script, Bilingual, Mixed Script, Input Search?
    e.g. for a Movie Hotkey flow: "@Lang Regional Script — Verify movie listings and titles render correctly in the regional script for the selected language"
    → Count them. ADD any missing ones, placed LAST after all functional cases.

  COUNT / STATE BOUNDARIES (for features that display a list or count-driven content):
  ✓ Zero items: e.g. "Verify an empty state message is shown when no virtual numbers are available for the listing"
  ✓ Single item: e.g. "Verify a single virtual number is shown inline without a panel when exactly one number is available"
  ✓ Multiple items: e.g. "Verify a scrollable panel appears when more than 2 virtual numbers are available"
  → ADD whichever boundary states are missing.

  NEGATIVE CASES:
  ✓ Are there at least 2 negative test cases? If not → ADD: one invalid-input case + one error/blocked-access case.

  SECURITY (critical flows only — payment, KYC, OTP/auth, contract data):
  ✓ Is there a security/data-masking step embedded within the relevant critical-flow test case?
    e.g. Step inside KYC TC: "Verify that uploaded document details are masked and not exposed in network responses or logs"
    → If MISSING → ADD it as a step inside the critical-flow TC (not a separate TC).

  Only after BOTH passes are complete, return the JSON.

EXAMPLE DATA FIELD — optional, context-driven. Leave "examples" as empty string "" whenever you are not confident it adds real value.
  GOLDEN RULE: empty is always better than invented or irrelevant data.
  Only populate "examples" when the requirement or user input gives you clear, concrete data dimensions to work with.

  WHEN TO POPULATE:

  TYPE A — Search / filter / browse / booking features where input combinations matter:
    Only if the requirement mentions specific categories, cities, brands, or ranges — use those exact values.
    If requirement is generic (no specific data mentioned), leave empty.
    Format: 3–5 varied rows of real input combinations.
    e.g. (only if requirement mentions vehicle search with city/brand/budget):
      City: Mumbai | Category: SUV | Brand: Maruti Suzuki | Budget: ₹8L–₹15L
      City: Pune | Category: Sedan | Brand: Hyundai | Budget: ₹6L–₹10L

  TYPE B — Condition/state-based tests (flows, contract types, KYC, session, platform behaviour, functional rules):
    Only if the requirement explicitly defines distinct states, roles, or conditions.
    Describe those conditions as short labels — do NOT invent states not in the requirement.
    e.g. (only if requirement defines contract tiers):
      Contract: Paid Platinum → premium badge visible
      Contract: Non-Paid → upgrade prompt shown
      Contract: Paid Expired → downgraded UI
    e.g. (only if requirement defines campaign gating):
      Campaign: Active → proceed to next step
      Campaign: Inactive → redirect to self-signup
    e.g. (only if requirement defines document rules):
      Document: ID Proof | Age: 3 yrs | Status: Approved → alert + delete
      Document: Shop Image | Age: 1 yr | Status: Approved → no action

  TYPE D — API / backend tests where endpoint + payload + status are defined in the requirement:
    Only if the requirement or context specifies the endpoint, fields, or expected status codes.
    e.g.:
      POST /sync/instagram | token: valid | account_type: professional → 200 OK
      POST /sync/instagram | token: expired → 401 Unauthorized

  WHEN TO LEAVE EMPTY (always use "" in these cases):
    - @Lang, layout, or pure visual/rendering tests
    - Generic functional tests where no specific data is mentioned in the requirement
    - Any test where you would have to invent data not grounded in the requirement
    - When unsure — default to empty

Return STRICT JSON only:

{{
  "positive_tests": [
    {{
      "title": "...",
      "steps": ["...", "..."],
      "examples": "City: Mumbai | Category: SUV | Brand: Maruti\nCity: Pune | Category: Sedan | Brand: Hyundai"
    }}
  ],
  "negative_tests": [
    {{
      "title": "...",
      "steps": ["...", "..."],
      "examples": "City: Delhi | Input: empty search\nCity: Bengaluru | Input: special characters only"
    }}
  ]
}}
"""