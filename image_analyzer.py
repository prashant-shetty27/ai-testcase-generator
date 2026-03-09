"""
image_analyzer.py

Step 1 of image-based test case generation:
  - Send the uploaded screenshot/mockup to GPT-4o vision
  - Extract: feature description, visible UI elements, platform hints,
    modules, pages, and business rules apparent from the UI
  - Return a structured dict that can be fed directly into the
    existing generate_full_test_suite() pipeline

Step 2 (test generation) is handled by the existing pipeline unchanged.
"""

import json
import re
from ai_service import ask_ai_with_image


# -------------------------------------------------------
# KNOWN MODULE & PAGE KEYWORDS (mirrors context_builder)
# -------------------------------------------------------

KNOWN_MODULES = {
    "login", "search", "catalogue", "verticals", "profile",
    "payment gateway", "reviews ratings", "chatbot", "kyc",
    "contract", "movies",
}

# Full set of valid page enum values accepted by TestGenerationRequest
VALID_PAGE_ENUMS = {
    "login_page", "home_page", "result_page", "details_page", "prp_page",
    "pdp_page", "catalogue_page", "leads_dashboard", "analytics_dashboard",
    "leads_page", "edit_listings_page", "free_listings_page",
    "payment_gateway_page", "user_profile_page", "settings_page",
    "reports_page", "search_page", "notification", "reviews_ratings",
    "ubl_android_app", "ubl_ios_app", "vn_an_dvn_calls",
    "leads_dashboard_page", "analytics_dashboard_page",
    "web_b2b_rfq_page", "web_b2b_home_page", "web_b2b_prp_page",
    "web_b2b_pdp_page", "web_b2b_catalogue_page",
    "touch_b2b_rfq_page", "touch_b2b_home_page", "touch_b2b_prp_page",
    "touch_b2b_pdp_page", "touch_b2b_catalogue_page",
    "android_b2b_rfq_page", "android_b2b_home_page", "android_b2b_prp_page",
    "android_b2b_pdp_page", "android_b2b_catalogue_page",
    "ios_b2b_rfq_page", "ios_b2b_home_page", "ios_b2b_prp_page",
    "ios_b2b_pdp_page", "ios_b2b_catalogue_page",
    "autosuggest", "chatbot", "voice_assistant", "api_authentication",
    "genio", "cs", "dc", "kyc", "de_cs", "sales", "finance", "data",
    "performance", "security", "others",
}

# Human-readable aliases → enum value
PAGE_ALIAS_MAP = {
    "result page": "result_page",
    "details page": "details_page",
    "profile page": "user_profile_page",
    "user profile page": "user_profile_page",
    "edit listings page": "edit_listings_page",
    "payment gateway page": "payment_gateway_page",
    "reviews ratings": "reviews_ratings",
    "login page": "login_page",
    "home page": "home_page",
    "search page": "search_page",
    "catalogue page": "catalogue_page",
    "settings page": "settings_page",
    "leads page": "leads_page",
    "reports page": "reports_page",
    "free listings page": "free_listings_page",
}

KNOWN_PLATFORMS = {
    "web", "touch", "mobile web", "android app", "ios app",
    "hybrid app", "api",
}


def _normalise_page(raw: str) -> str | None:
    """Map a raw page string to a valid enum value, or return None if unknown."""
    cleaned = raw.strip().lower()
    # Direct alias match
    if cleaned in PAGE_ALIAS_MAP:
        return PAGE_ALIAS_MAP[cleaned]
    # Try replacing spaces with underscores
    underscored = cleaned.replace(" ", "_")
    if underscored in VALID_PAGE_ENUMS:
        return underscored
    # Already a valid enum value
    if cleaned in VALID_PAGE_ENUMS:
        return cleaned
    return None


def _extract_json(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned.strip())
    return json.loads(cleaned)


def analyze_image_for_testcases(
    image_path: str,
    extra_context: str = "",
    platforms_hint: list[str] | None = None,
) -> dict:
    """
    Analyse a UI screenshot/mockup and return a structured requirement dict
    compatible with the test generation pipeline.

    Returns:
    {
        "requirement":   str,   — synthesised requirement text describing what the UI does
        "feature":       str,   — short feature label (used as memory key)
        "platforms":     list,
        "modules":       list,
        "pages":         list,
        "test_types":    list,
        "business_rules": list, — business rules visible in the UI
        "constraints":   list,
        "image_summary": str,   — human-readable description of what the image shows
    }
    """

    platform_hint_text = ""
    if platforms_hint:
        platform_hint_text = (
            f"\nThe tester has specified these target platforms: {', '.join(platforms_hint)}.\n"
            "Use these as the primary platforms in your output."
        )

    extra_text = ""
    if extra_context and extra_context.strip():
        extra_text = f"\nAdditional context from the tester:\n{extra_context.strip()}\n"

    prompt = f"""
You are a senior QA architect analysing a UI screenshot or design mockup.

{platform_hint_text}
{extra_text}

Your task:
1. Identify the feature shown in this image (e.g., Search Result Page, Login Screen, KYC Upload, Movie Booking).
2. Describe all visible UI elements: fields, buttons, labels, dropdowns, sections, error states, icons.
3. Infer the business rules and validation logic visible in the UI.
4. Identify which platform this UI targets based on visual cues (mobile browser, desktop web, native app, etc.).
5. Synthesise a complete requirement description as a QA engineer would write it for test case generation.

Return STRICT JSON only:

{{
  "feature": "<short feature name, e.g. NCT Result Page>",
  "image_summary": "<2-3 sentence plain-English description of what this screen shows>",
  "requirement": "<full synthesised requirement text — 3-10 sentences — as if a product manager wrote it>",
  "platforms": ["<platform1>", "<platform2>"],
  "modules": ["<module1>"],
  "pages": ["<page1>"],
  "test_types": ["functional", "ui"],
  "business_rules": ["<rule1>", "<rule2>"],
  "constraints": ["<constraint1>"]
}}

Platform values must be from: web, touch, android app, ios app, hybrid app, api.
Module values must be from: login, search, catalogue, verticals, profile, payment gateway, reviews ratings, chatbot, kyc, contract, movies.
Page values must be from (use exact underscore format): result_page, details_page, home_page, login_page, search_page, user_profile_page, catalogue_page, edit_listings_page, payment_gateway_page, reviews_ratings, kyc, others.
If unsure about module/page, omit them — do NOT invent values.
"""

    raw = ask_ai_with_image(image_path, prompt, expect_json=True)

    try:
        parsed = _extract_json(raw)
    except Exception:
        # Fallback: treat whatever the model said as the requirement
        parsed = {
            "feature": "UI Screen",
            "image_summary": raw[:300] if raw else "Could not parse image.",
            "requirement": raw if raw else "Generate test cases for the uploaded UI screen.",
            "platforms": platforms_hint or ["touch"],
            "modules": [],
            "pages": [],
            "test_types": ["functional", "ui"],
            "business_rules": [],
            "constraints": [],
        }

    # If the tester specified platforms, those take precedence
    if platforms_hint:
        parsed["platforms"] = platforms_hint

    # Normalise platforms to known keys
    raw_platforms = parsed.get("platforms") or []
    normalised = []
    for p in raw_platforms:
        pl = p.strip().lower()
        if pl in KNOWN_PLATFORMS:
            normalised.append(pl)
        elif "mobile" in pl or "touch" in pl:
            normalised.append("touch")
        elif "android" in pl and "app" in pl:
            normalised.append("android app")
        elif "ios" in pl and "app" in pl:
            normalised.append("ios app")
        elif "web" in pl:
            normalised.append("web")
    parsed["platforms"] = normalised if normalised else (platforms_hint or ["touch"])

    # Normalise modules to known values
    parsed["modules"] = [
        m for m in (parsed.get("modules") or [])
        if m.strip().lower() in KNOWN_MODULES
    ]
    # Normalise pages to valid enum values — drop any that can't be mapped
    normalised_pages = []
    for p in (parsed.get("pages") or []):
        mapped = _normalise_page(p)
        if mapped:
            normalised_pages.append(mapped)
    parsed["pages"] = normalised_pages

    # Ensure required keys exist
    parsed.setdefault("test_types", ["functional", "ui"])
    parsed.setdefault("business_rules", [])
    parsed.setdefault("constraints", [])

    return parsed
