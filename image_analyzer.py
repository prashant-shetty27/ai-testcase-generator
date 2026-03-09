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

KNOWN_PAGES = {
    "result page", "details page", "profile page", "user profile page",
    "reviews ratings", "edit listings page", "payment gateway page", "kyc",
}

KNOWN_PLATFORMS = {
    "web", "touch", "mobile web", "android app", "ios app",
    "hybrid app", "api",
}


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
Page values must be from: result page, details page, profile page, user profile page, reviews ratings, edit listings page, payment gateway page, kyc.
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

    # Normalise modules and pages to known values
    parsed["modules"] = [
        m for m in (parsed.get("modules") or [])
        if m.strip().lower() in KNOWN_MODULES
    ]
    parsed["pages"] = [
        p for p in (parsed.get("pages") or [])
        if p.strip().lower() in KNOWN_PAGES
    ]

    # Ensure required keys exist
    parsed.setdefault("test_types", ["functional", "ui"])
    parsed.setdefault("business_rules", [])
    parsed.setdefault("constraints", [])

    return parsed
