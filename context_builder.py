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
            "Accessibility (WCAG 2.1 AA): minimum 4.5:1 contrast ratio for normal text, 3:1 for large text and UI components; all interactive elements (buttons, inputs, links) must be keyboard-reachable via Tab/Enter; every button, input field, and image must have a descriptive label readable by screen readers (VoiceOver, NVDA); error messages must be programmatically associated with their input field",
            "Incognito / private browsing mode behavior"
        ],

        "touch": [
            "Android browsers (primary): Chrome for Android, Samsung Internet (default browser on Samsung devices) — test both separately",
            "iOS browsers (primary): Safari for iOS, Chrome for iOS — test both separately",
            "NOTE: Firefox Mobile is NOT a target browser for mobile web; do not generate Firefox test cases for touch platform",
            "Screen sizes: 5.4-inch (compact), 6.1-inch (standard), 6.7-inch (Plus/Max/Samsung S/A series) — test each layout breakpoint",
            "Samsung devices (6.7-inch): validate city and vehicle-type sections do not wrap or overflow in Samsung Internet",
            "Gestures: tap, long-press, swipe, pinch-to-zoom, double-tap — must all be validated",
            "Orientation: portrait and landscape — UI must reflow correctly on all target screen sizes",
            "Virtual keyboard: input fields must scroll above keyboard; no content hidden behind it",
            "Network conditions: 4G, 3G, 2G, offline — test graceful degradation",
            "Viewport meta tag behavior — no horizontal scroll on any screen size",
            "iOS Safari vs Android Chrome rendering differences — test separately",
            "Touch target sizes: minimum 44x44px tap targets — verify on smallest supported screen",
            "No app-specific lifecycle (background/foreground) tests — this is a mobile touch website, not a native app"
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
            "User types must always be tested separately: NEW/Unregistered user vs EXISTING/Registered user — behaviors differ and must NOT be collapsed into one test case",
            "New/Unregistered user: registration flow, mobile OTP delivery and validation, first-time profile setup, duplicate mobile number prevention",
            "Existing/Registered user: valid login with correct credentials, login after session expiry, remembered credentials/auto-fill behavior",
            "Valid and invalid credential validation — for both user types",
            "Account lock after N consecutive failed attempts — verify lock message and unlock flow",
            "Password policy enforcement: minimum length, special characters, common password rejection",
            "CAPTCHA validation: appears after threshold attempts, refresh works, wrong CAPTCHA blocked",
            "Session timeout behavior: redirect to login, session data cleared, no ghost session",
            "Concurrent login handling: same account on two devices — older session must be invalidated or warned",
            "Social/OTP login: OTP expiry, resend OTP cooldown, wrong OTP rejection",
            "Forgot password: link expiry, one-time use, redirect after reset"
        ],
        "search": [
            "Empty search behavior",
            "Typo/partial keyword handling",
            "Autosuggest relevance and de-duplication",
            "Category and company intent matching",
            "Result relevance and ranking consistency",
            "Pagination and infinite-scroll consistency",
            "Recent search persistence and recall",
            "Performance with large dataset",
            # Location-aware search rules (applies to category/company/product/service/business/movies searches)
            "LOCATION: GPS-detected city auto-fills search location — verify results match that city only",
            "LOCATION: User manually changes location mid-session — results must refresh to new city/area immediately",
            "LOCATION: Location permission DENIED — app must fall back to manual city selection, not crash or show empty results",
            "LOCATION: Location permission GRANTED then revoked from settings — graceful degradation required",
            "LOCATION: Hyperlocal search (area/pincode level) — results must be tighter than city-level and ranked by proximity",
            "LOCATION: 'Near me' or proximity search — results must be sorted by distance from user's GPS coordinates",
            "LOCATION: User in City A searches with location set to City B — results must reflect City B, not current GPS city",
            "LOCATION: Boundary area (city limits / multi-city zones like Mumbai-Thane, Delhi-Gurgaon, Bengaluru-Whitefield) — results must not bleed across city boundaries unless explicitly requested",
            "LOCATION: Low GPS accuracy (indoors, basement, rural) — system must show accuracy warning or fallback option",
            "LOCATION: Movies search — city determines multiplex list; changing city must refresh cinema/showtime results instantly",
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
            # ── Core behaviour ──
            "Intent recognition: chatbot must correctly identify the vertical from the user's query — e.g. 'need a plumber' → Home Services, 'book a table' → Restaurants, 'find a dentist' → Healthcare",
            "Fallback: when intent is ambiguous or unrecognised, chatbot must ask a clarifying question — NOT return a blank response or generic error",
            "Conversation context continuity: follow-up messages must retain the context of prior turns — e.g. 'in Mumbai' after 'find a salon' must refine the previous result, not restart",
            "Location context: chatbot must use the user's currently selected city as the default location unless the user explicitly names a different city in the query",
            "Multi-turn correction: if user corrects a previous message ('I meant Pune, not Mumbai'), chatbot must update results accordingly in the same session",
            "Empty / gibberish input: chatbot must NOT crash or return null — must respond with a helpful prompt to try again",
            "Language input: chatbot must accept and correctly process queries in Hindi, English, and regional languages — do not ignore or error on regional script input",
            # ── Vertical coverage — chatbot must handle queries for ALL of these ──
            "Vertical — Restaurants & Food: queries like 'best biryani near me', 'pure veg restaurant in Pune', 'open now restaurants' — must return relevant listings with cuisine, rating, locality",
            "Vertical — Auto / Vehicles: queries like 'used cars in Hyderabad', 'bike service centre near me', 'Maruti Swift price' — must map to Auto vertical and surface relevant listings or filters",
            "Vertical — Real Estate / Property: queries like 'flats for rent in Bengaluru', '2BHK sale in Andheri', 'PG near Koramangala' — must distinguish sale vs rent vs PG correctly",
            "Vertical — Healthcare / Doctors: queries like 'cardiologist near me', 'Apollo Hospital contact', 'eye specialist in Delhi' — must return clinic/doctor listings with speciality and location",
            "Vertical — Home Services: queries like 'plumber in Mumbai', 'AC repair Noida', 'electrician near me' — must map to correct service sub-category",
            "Vertical — Beauty & Wellness: queries like 'hair salon in Bandra', 'spa near me', 'unisex parlour in Chennai' — must return correct salon/spa listings",
            "Vertical — Education: queries like 'MBA colleges in Pune', 'spoken English classes near me', 'NEET coaching in Delhi' — must map to Education vertical with course/institute filter",
            "Vertical — Hotels & Travel: queries like 'hotels near airport Mumbai', 'budget stay in Goa', 'travel agent in Delhi' — must surface hotel or travel agent listings",
            "Vertical — Jobs & Recruitment: queries like 'data analyst jobs in Bengaluru', 'freshers job openings', 'placement consultancy near me' — must route to Jobs vertical",
            "Vertical — Movies & Entertainment: queries like 'movies playing today in Chennai', 'IMAX theatres in Mumbai', 'movie timings for [film name]' — must surface cinema listing for selected city",
            "Vertical — Finance & Insurance: queries like 'car insurance in Hyderabad', 'CA near me', 'tax consultant in Pune' — must map to Finance vertical correctly",
            "Vertical — Legal Services: queries like 'property lawyer in Delhi', 'notary near me', 'consumer court advocate' — must route to Legal vertical",
            "Vertical — Matrimony: queries like 'matrimonial services in Mumbai', 'Hindu wedding bureau in Chennai' — must route to Matrimony vertical",
            "Vertical — Pets: queries like 'vet near me', 'dog grooming in Bengaluru', 'pet shop in Delhi' — must route to Pets vertical",
            "Vertical — Events & Photographers: queries like 'wedding photographer in Jaipur', 'event management company Mumbai' — must route to Events vertical",
            # ── Cross-vertical and edge cases ──
            "Cross-vertical ambiguity: query 'gym near me' could map to Fitness or Healthcare — chatbot must pick the most relevant vertical or ask a clarifying question, not drop the query",
            "Vertical switch mid-session: user asks about restaurants then asks about plumbers — chatbot must switch context cleanly without mixing results",
            "Multi-entity query: 'dentist and pharmacy near Koramangala' — chatbot must handle multi-intent queries by either returning both or asking which to address first",
            "No results for vertical + city combo: chatbot must say 'No results found in [city] for [category]' and suggest nearby city or broader search — never return an empty silent response",
            "Business name search: 'contact number of Hotel Taj Mumbai' — chatbot must surface the specific business PDP, not a generic category result",
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
        ],

        "contract": [
            "Contract types must ALWAYS be tested separately — do NOT merge types into a single test case",
            "Paid - Platinum: highest tier, all premium features unlocked, validate Platinum-exclusive benefits",
            "Paid - Diamond: second tier, validate Diamond-specific features differ from Platinum",
            "Paid - Normal: standard paid tier, validate basic paid features, no Platinum/Diamond extras",
            "Paid - National Listing: pan-India visibility, validate national-level display rules",
            "Paid - Other: any non-standard paid category, validate feature access matches tier definition",
            "Non-Paid: free listing, premium features must be blocked with upgrade prompt visible",
            "Paid Expired: previously paid, now expired — premium features must be revoked, downgrade UI shown",
            "Contract renewal: Paid Expired → Paid transition must restore all features immediately without page reload",
            "Status transitions must not bleed across types: Platinum rules must never apply to Diamond or Normal",
            "Contract status change must reflect in UI immediately — no stale state after plan upgrade/downgrade",
            "Revenue-critical: Paid Expired must not display as Active Paid anywhere in the UI or API response"
        ],

        "calls": [
            # ── Number type definitions ──
            "VN (Virtual Number): Fixed number allocated ONLY to PAID clients — single mobile-type number, never changes",
            "DVN (Dynamic Virtual Number): Range of fixed numbers allocated to NON-PAID businesses — number CHANGES after cache clear, session end, or ~1 minute; must be tested for each expiry trigger",
            "Actual Number: For PAID clients who opted out of VN, OR emergency services / helplines — can be single or multiple numbers (mobile, landline, tollfree)",
            "Preferred Number: Actual number (mobile/landline/tollfree) fetched from Google when JD does not have the number — behaves identically to Actual Number for display and routing",
            # ── Platform-specific display rules ──
            "WEB + VN: Display the fixed VN number DIRECTLY on the page (no 'Show Number' button) — single mobile-type number only",
            "WEB + DVN: Display the DVN number directly on the page — number must change after cache clear, session expiry, or ~1-minute interval; verify the new number is still from the allocated DVN range",
            "WEB + Actual / Preferred: Show 'Show Number' button — on click reveals single or multiple numbers (all number types: mobile, landline, tollfree)",
            "TOUCH / APP + VN: Show 'Show Number' button — on tap reveals single mobile-type VN number",
            "TOUCH / APP + DVN: Show number (or Show Number button per platform) — number must rotate after cache clear, session end, or ~1-minute TTL; verify each rotation gives a valid DVN range number",
            "TOUCH / APP + Actual / Preferred: Show 'Show Number' button — on tap reveals single or multiple numbers",
            # ── DVN-specific rotation rules ──
            "DVN rotation trigger 1: Hard browser/app cache clear — number must change on next load",
            "DVN rotation trigger 2: Session expiry — new session must get a different DVN from the pool",
            "DVN rotation trigger 3: ~1-minute TTL — revisiting the same listing after 60+ seconds must show a different DVN",
            "DVN pool exhaustion: when all numbers in the range are allocated, system must not crash or show null — must recycle or queue gracefully",
            # ── Actual / Preferred number rules ──
            "Actual Number — single number: button reveals one number; verify correct formatting (mobile 10-digit, landline with STD, tollfree 1800-series)",
            "Actual Number — multiple numbers: button reveals list; verify all numbers are displayed, none truncated",
            "Preferred Number: sourced from Google; display and routing must be identical to Actual Number; must not be misclassified as VN or DVN",
            # ── Cross-cutting rules ──
            "Number masking: before user clicks 'Show Number', number must be partially masked or hidden — not visible in page source or API response",
            "Call tracking: every number reveal must log a lead event — verify lead is recorded for VN, DVN, Actual, and Preferred types separately",
            "Non-paid business with VN: should NOT be possible — verify VN is blocked for non-paid contracts",
            "Paid client with DVN: should NOT be possible — verify DVN is blocked for paid contracts with active VN",
            "Emergency / helpline numbers (Actual): must always display regardless of contract status — never blocked by paid/non-paid rules",
        ],

        "movies": [
            "City selection must filter multiplex listings correctly — results must match selected city only",
            "Genre, language, and format filters (2D, 3D, IMAX, 4DX, Dolby) must work independently and in combination",
            "Showtime accuracy: verify seat availability is real-time and synced before and after booking",
            "Booking flow: seat selection → payment → confirmation ticket — validate each step transition",
            "Sold-out seats must be visually disabled and non-selectable; booking attempt on sold-out must be blocked",
            "Show cancellation and refund: validate refund eligibility window, refund amount accuracy, and status update",
            "Duplicate booking prevention: same user booking same seat for same show must be blocked",
            "Midnight shows and back-to-back same-day shows: date boundary handling must be correct",
            "Language filter: regional vs English — results must match filter exactly, no cross-language bleed",
            "Certificate rating display: U, UA, A — age-restricted content must display rating prominently",
            "Show expired / no longer screening: must show appropriate 'no longer available' message, not a broken page or 500 error",
            "Deep link to movie detail page: back navigation must return to correct listing, not home",
            "Movie thumbnail, title, and rating data must match across result page and detail page",
            "Ticket PDF/QR code: valid format, barcode scannable, correct show details on ticket"
        ],

        "restaurants": [
            "Cuisine filter: multi-select (e.g. North Indian + Chinese) must AND filters correctly and return only matching listings",
            "Veg / Non-Veg / Vegan filter: results must honour selection strictly — no cross-contamination in results",
            "Open Now filter: only restaurants with current operating hours within range must appear",
            "Rating filter: minimum rating threshold must exclude all listings below it",
            "Home delivery / Dine-in / Takeaway toggle: must switch listing set correctly without page reload",
            "City + locality drill-down: area-level search (e.g. Bandra, Koramangala) must narrow results within that zone",
            "No results for cuisine + city combo: must show empty state with suggestion to broaden search",
            "Restaurant detail page: menu, timings, address, contact, photos — all must be accurate and actionable",
            "User reviews: sort by latest, highest, lowest — ordering must be accurate",
            "Booking / reservation CTA: if available, must open correct booking flow with pre-filled restaurant details"
        ],

        "real estate": [
            "Property type filter: Flat, Villa, Plot, PG, Co-living — each must return distinct listing sets",
            "Transaction type: Sale vs Rent vs Lease — must never bleed across; a sale listing must not appear in rent results",
            "BHK filter: 1BHK, 2BHK, 3BHK, 4BHK+ — results must match exactly; combination filters must AND correctly",
            "Budget / price range filter: min–max range must exclude all out-of-range listings",
            "Locality filter: area-level results (e.g. Andheri, Whitefield) must not include listings from adjacent areas unless user selects them",
            "Furnished / Semi-Furnished / Unfurnished: must filter correctly and match listing details",
            "Verified listings badge: must only appear on verified listings — unverified must not show badge",
            "PG-specific filters: single / double / triple sharing, male / female / co-ed — each must return correct set",
            "Map view: listing pins must correspond to actual property locality — no geo-mismatch",
            "Contact agent / Request callback CTA: must trigger correct lead flow with pre-filled property details"
        ],

        "healthcare": [
            "Speciality filter: Cardiologist, Dermatologist, Dentist, ENT, Gynaecologist, Orthopaedic etc. — each must return only matching doctors/clinics",
            "Consultation type: In-Clinic vs Online (Teleconsultation) — must filter correctly; online-only doctors must not appear in in-clinic results",
            "Availability / Next slot: must reflect real-time slot data — expired slots must not be bookable",
            "Hospital vs Individual Doctor search: must route to correct listing type and detail page",
            "Multi-city clinic: doctor with multiple clinic locations — each location must have its own slot calendar",
            "Emergency / 24x7 filter: only hospitals or clinics with round-the-clock service must appear",
            "Insurance accepted filter: results must only show providers accepting the selected insurance",
            "Appointment booking flow: select doctor → select slot → fill patient details → confirm — each step must be validated",
            "Appointment cancellation and rescheduling: must update calendar in real-time, send confirmation notification",
            "Rating and review for doctors: must be aggregated correctly and reflect only verified patient reviews"
        ],

        "home services": [
            "Service category filter: Plumber, Electrician, Carpenter, Painter, AC Repair, Pest Control, Cleaning — each must return only relevant providers",
            "Locality filter: service providers listed must operate in the selected area — out-of-area providers must not appear",
            "Verified / Background-checked badge: must only appear on verified providers",
            "Availability filter: available today / this week — must reflect provider's real-time slot availability",
            "Request callback / Book now CTA: must pre-fill service category and user location in lead form",
            "Provider rating and reviews: must be sorted and filtered correctly (highest first, most recent first)",
            "No service available in area: must show empty state with 'No providers in this area' message and suggestion to expand radius",
            "Provider detail page: service list, pricing (if shown), contact, area coverage — all must be accurate",
            "Multiple service categories per provider: if a provider offers both plumbing and electrical, both must be discoverable via respective searches"
        ],

        "beauty": [
            "Service type filter: Hair, Skin, Nail, Spa, Makeup, Waxing — each must return only matching salons",
            "Gender filter: Male / Female / Unisex — must filter salon listings correctly",
            "At-home service vs In-salon toggle: must switch listing set correctly",
            "Locality filter: area-specific results must not include salons outside that area",
            "Slot booking flow: select service → select slot → confirm — must validate each step",
            "Cancellation policy: must be visible before booking confirmation",
            "Package / combo offers: if listed, pricing must be accurate and applied correctly at checkout",
            "Rating and reviews: verified reviews only; sort by latest and highest must work correctly"
        ],

        "education": [
            "Course / class type filter: School Tuition, Competitive Exam Coaching, Skill Development, Language, Dance, Music — each must return correct institutes",
            "Board / exam filter: CBSE, ICSE, State Board, IIT-JEE, NEET, UPSC, CAT — must narrow results correctly",
            "Mode of learning: Online vs Offline vs Hybrid — must filter correctly; online-only institutes must not appear in offline results",
            "Locality filter: area-level results for offline institutes must be accurate",
            "Fee range filter: institutes outside the range must be excluded",
            "Demo class / enquiry CTA: must open lead form with pre-filled course and institute details",
            "Institute detail page: courses offered, batch timings, faculty, fees, contact — all must be accurate",
            "No results for exam + city combo: must show empty state with broader search suggestion"
        ],

        "hotels": [
            "Check-in / Check-out date picker: must block past dates; check-out must always be after check-in",
            "Guest count filter: adults + children — room results must match occupancy capacity",
            "Budget filter: min–max price per night — out-of-range properties must not appear",
            "Property type: Hotel, Homestay, Resort, Hostel, Service Apartment — each must return distinct listing sets",
            "Amenity filter: WiFi, Pool, Gym, Breakfast Included, AC — multi-select must AND filters correctly",
            "Locality / landmark search: 'hotels near airport', 'hotels in Bandra' — results must be proximity-accurate",
            "Availability: if no rooms available for selected dates, must show 'Sold out' and not allow booking",
            "Room type selection: Single, Double, Suite — must show correct pricing per room type",
            "Booking flow: select room → enter guest details → payment → confirmation voucher — each step validated",
            "Cancellation policy: must be clearly shown before payment; free vs paid cancellation must be accurate"
        ],

        "jobs": [
            "Job role / designation filter: must return only listings matching the searched role",
            "Experience filter: Fresher, 1–3 yrs, 3–5 yrs, 5–10 yrs, 10+ yrs — must return correctly scoped results",
            "Salary range filter: min–max CTC — out-of-range jobs must be excluded",
            "Job type: Full-Time, Part-Time, Freelance, Internship, Work From Home — each must return distinct sets",
            "Industry / sector filter: IT, Healthcare, Finance, Education, Manufacturing etc. — must narrow results accurately",
            "City filter: remote jobs must appear regardless of city; non-remote must match selected city",
            "Posted date filter: Last 24 hrs, Last 7 days, Last 30 days — must exclude older postings",
            "Apply now CTA: must open correct application form with pre-filled job title and company",
            "Job detail page: role, company, salary, location, skills required, JD — all must be accurate and complete",
            "Saved / bookmarked jobs: must persist across sessions for logged-in users"
        ],

        "finance": [
            "Service type filter: CA / Chartered Accountant, Tax Consultant, Insurance Agent, Loan Agent, Financial Advisor — each must return correct provider listings",
            "Insurance sub-type: Life, Health, Motor, Travel — must filter independently",
            "Locality filter: area-level results must be accurate for in-person service providers",
            "Verified / IRDA-registered badge: must only appear on verified insurance providers",
            "Enquiry / callback CTA: must pre-fill service type and user location",
            "Provider detail page: services offered, contact, registration number (if applicable) — all must be accurate",
            "No provider in area: must show empty state with broader search or online service suggestion"
        ],

        "legal": [
            "Practice area filter: Property, Criminal, Family, Corporate, Consumer, Labour — each must return only matching advocates/firms",
            "Locality filter: court-specific or area-specific searches must return accurate results",
            "Experience filter: years of practice — must narrow results correctly",
            "Consultation mode: In-Person vs Online — must filter correctly",
            "Verified / Bar Council registered badge: must only appear on verified advocates",
            "Enquiry CTA: must open lead form with pre-filled practice area and location",
            "Advocate detail page: practice areas, experience, contact, bar council number — all must be accurate"
        ],

        "matrimony": [
            "Religion / community filter: Hindu, Muslim, Christian, Sikh, Jain, Buddhist, sub-community — must return only matching profiles or bureaus",
            "City / state filter: must return bureaus or profiles operating in that location",
            "Service type: Matrimonial Bureau vs Online Profile Listing — must filter correctly",
            "Contact bureau CTA: must open lead form with pre-filled religion and city",
            "Bureau detail page: services offered, membership plans, contact — all must be accurate",
            "No bureau in city: must show empty state with nearest city suggestion"
        ],

        "pets": [
            "Service type filter: Veterinary Clinic, Pet Shop, Dog Grooming, Pet Boarding, Pet Training — each must return correct listings",
            "Pet type filter: Dog, Cat, Bird, Fish, Reptile — must narrow results to providers supporting that pet type",
            "Locality filter: area-specific results must be accurate",
            "Emergency vet filter: 24x7 / emergency clinics must only appear if tagged correctly",
            "Appointment booking: must open correct booking flow for vet clinics",
            "Provider detail page: services, timings, contact, pet types supported — all must be accurate"
        ],

        "events": [
            "Event type filter: Wedding, Corporate, Birthday, Concert, Exhibition, Sports — each must return correct vendors",
            "Service category: Event Planner, Decorator, Caterer, Photographer, Videographer, DJ, Venue — each must be independently searchable",
            "City filter: event vendors must be scoped to selected city",
            "Budget range filter: out-of-range vendors must be excluded",
            "Availability / date-specific search: vendor must show as unavailable if booked for the requested date",
            "Portfolio / gallery: must display correctly on detail page without broken images",
            "Enquiry CTA: must pre-fill event type, date, and city in lead form",
            "Vendor detail page: services, past events portfolio, pricing range, contact — all must be accurate",
            "No vendor for event type + city combo: must show empty state with suggestion"
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
            # ── Search-to-page routing rules (CRITICAL) ──
            "ROUTING RULE: Category search (via autosuggest OR freetext) ALWAYS lands on Result Page — generate category-focused listing test cases here",
            "ROUTING RULE: Company/brand name search ALWAYS lands on Details Page (PDP) — do NOT generate company profile test cases on result page",
            "ROUTING EXCEPTION: Company freetext search OR outlet-grouped search (e.g. 'Pizza Hut', 'McDonald's outlets') lands on Company Result Page — a special result page showing multiple outlet listings of that company, NOT a category result page",
            # ── Result page content rules ──
            "Result count accuracy — verify total count matches applied category and location filters",
            "Filter/sort: category, sub-category, rating, distance, verified badge — each filter must independently narrow results; combinations must AND correctly",
            "Vertical/vehicle-type filters displayed below city header — @Car, @Bike, @Truck, @Commercial etc. must each return distinct, correctly-filtered listing sets",
            "Sponsored / premium listings must be visually distinct (badge/highlight) and appear in correct positions",
            "Pagination and infinite scroll — boundary: last page, empty page, scroll-to-top",
            "No-result state: friendly message with alternative suggestions shown; no blank page, no 500 error",
            "Weak network / offline: skeleton loader or cached results shown; retry CTA available",
            "Back navigation from Details Page must restore result page at same scroll position with filters intact",
            "Sorting options (relevance, rating, distance, newest) — each must reorder listing set correctly",
            "For B2B result page: vehicle type section below city must be a primary navigational element — missing or broken vehicle type display is a critical defect",
        ],
        "details page": [
            # ── Search-to-page routing rules (CRITICAL) ──
            "ROUTING RULE: Company/brand name search ALWAYS lands on Details Page — generate company profile, contact, and location test cases here",
            "ROUTING RULE: Category searches do NOT land here — do NOT generate category listing test cases on details page",
            "ROUTING EXCEPTION: Company freetext / outlet search lands on Company Result Page, not this Details Page",
            # ── Details page content rules ──
            "Listing vs details data consistency — name, category, address must match across result page and details page",
            "Business contact data consistency — phone, email, website must be accurate and actionable",
            "Address / location consistency — map pin must match displayed address; directions must open correct map",
            "Ratings/reviews summary consistency — aggregate rating must match individual review count",
            "Back navigation must return to result page with previous scroll position and filters preserved",
            "Claimed vs unclaimed listing — UI must visually differentiate; claimed shows enhanced data fields",
            "Multiple branches: each branch must have its own details page; selecting a branch must update all contact data",
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
        "web b2b prp page": [
            "B2B PRP (Primary Result Page) = category search result for B2B context — all category-based test cases belong here",
            "Vehicle type / vertical filter below city is a PRIMARY navigational element — test each type separately (@Car, @Bike, @Truck, @Commercial, @Heavy Vehicle)",
            "Missing, broken, or misaligned vehicle type section is a CRITICAL defect — always verify it renders correctly",
            "B2B listings display must show company name, category, location, rating, and contact CTA correctly",
            "Filter combinations: location + category + vehicle type — must AND correctly and return non-empty or appropriate no-result state",
            "Back from B2B PDP (details) must restore PRP with filters and scroll position intact",
            "Sorting on B2B PRP: relevance, rating, distance — verify each reorders correctly for B2B listings",
            "No-result state on B2B PRP: show message relevant to B2B context (not consumer messaging)",
        ],
        "touch b2b prp page": [
            "B2B PRP on Touch: vehicle type section below city must render correctly on 5.4\", 6.1\", 6.7\" screens — no truncation or overflow",
            "Vehicle type filter chips/tabs must be horizontally scrollable if they overflow viewport width",
            "Tap target for vehicle type filters: minimum 44x44px — verify on smallest screen",
            "Filter/sort drawer on touch must open, apply, and close correctly without UI breakage",
            "Back navigation from B2B PDP restores PRP scroll position — no jump to top",
        ],
        "android b2b prp page": [
            "B2B PRP on Android app: vehicle type section below city must render correctly on all target screen sizes and Android OS versions",
            "Vehicle type filter selection must persist across background/foreground app lifecycle",
            "Filter state must survive screen rotation (portrait ↔ landscape)",
        ],
        "ios b2b prp page": [
            "B2B PRP on iOS app: vehicle type section must render correctly on iPhone SE, standard, Plus/Max sizes",
            "Dynamic Island / notch must not overlap vehicle type filter section on iPhone 14 Pro / 15 Pro",
            "Filter state must survive background/foreground app switch on iOS",
        ],
        "web b2b pdp page": [
            "B2B PDP (Primary Detail Page) = direct company/business detail in B2B context",
            "Do NOT generate category search or result page test cases here",
            "B2B-specific fields: GST number, company type, year of establishment, employee count — verify display accuracy",
            "Contact CTA on B2B PDP: VN/DVN/Actual number rules apply (paid/non-paid contract determines number type)",
            "Back from B2B PDP must return to B2B PRP with correct filters intact",
        ],
        "vn an dvn calls": [
            "WEB: VN listings must show the number inline — no button, no click required",
            "WEB: DVN listings must show number inline — verify number rotates on cache/session/TTL expiry",
            "WEB / TOUCH / APP: Actual and Preferred listings must show 'Show Number' button — number(s) revealed only on interaction",
            "Before reveal: number must not appear in DOM source, network response, or page meta — anti-scraping requirement",
            "After reveal: all numbers formatted correctly — 10-digit mobile, STD+landline, 1800-series tollfree",
            "Lead event fired on every reveal — verify in analytics/backend for all 4 number types",
            "DVN: after 60 seconds, refreshing listing must serve a different number from the DVN pool",
            "Multiple Actual numbers: all numbers displayed in list; tapping any number initiates call correctly",
            "Paid Expired contract: VN must be deactivated — verify number is no longer reachable / shown",
            "Non-paid → Paid upgrade: DVN must be replaced by VN within expected SLA — verify no DVN shown after upgrade",
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
