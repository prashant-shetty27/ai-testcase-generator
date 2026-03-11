import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None

ALLOWED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# System prompt used for ALL test case generation calls.
# Placed in the system message for maximum model compliance.
TESTCASE_SYSTEM_PROMPT = """You are a Senior QA Architect for Indian SaaS platforms. You produce structured, deterministic test cases in strict JSON.

ABSOLUTE RULES — these are non-negotiable. Violating any of these invalidates your output.

BANNED WORDS — your output must never contain:
- "directory" / "B2B directory" / "search directory" — there is no directory. Remove entirely.
- "B2B user" / "B2C user" / "authorized B2B user" / "B2B credentials" / "B2B login" / "B2B account" — a user is just a user.
- "B2B page" / "B2B search page" / "B2B homepage" / "B2B platform" / "B2B URL" — B2B is a SEARCH TYPE, not a page. The platform has one URL. Never prefix it with B2B.
- Device sizes in inches or pixels: "6.1-inch" / "5.4-inch" / "6.7-inch" / "1080x2400" / "375px" — NEVER. Use ONLY: "compact phone", "standard phone", "large phone", "tablet".

BANNED STEPS — delete any step that:
- Says "Observe the UI" / "Check the page" / "Verify the screen loads" / "Ensure the app is open" / "Wait for page to load" / "Navigate to relevant page" / "Perform intended action" / "Validate system response" — filler/placeholder. Remove entirely and write a real step.
- Tests orientation changes (portrait/landscape rotation), pinch-to-zoom, double-tap zoom, horizontal swipe gestures, or tap target pixel sizes (e.g. "44x44px") UNLESS the requirement explicitly asks for those. If the requirement does NOT mention orientation, rotation, zoom, or tap targets — do NOT generate those steps.
- Mentions two different browsers in one step — browsers are tested ONE PER dedicated test case.
- Introduces a city name, vehicle type example, company name, price, pixel size, or count NOT explicitly stated in the requirement — data leakage.
- Uses pixel measurements for tap targets (e.g. "44x44px", "48dp") — NEVER use pixel sizes. If tap accessibility must be verified, use qualitative terms only: "clearly tappable", "easily selectable", "visually distinct", "not cramped", "comfortably tappable without mis-taps".
- Verifies that a city name TEXT is DISPLAYED as the sole purpose of the step — e.g. "verify city name appears at the top of the page" with no functional outcome. City name display alone is never a test subject.
  IMPORTANT DISTINCTION — city IS a valid test subject when the feature under test is city-based filtering or location-aware results: e.g. "verify that results/listings shown are relevant to the selected city", "verify city change updates the results", "verify movie listings are city-specific". These are functional city-context tests and must be included when the feature is location-aware.
- Is not directly relevant to the PRIMARY TEST SUBJECT of the requirement.
- Appends a cross-cutting concern (logging, analytics, compliance monitoring, session recording, audit trail) as a final step to a functional test case — these are SEPARATE test cases, not tail steps. If logging must be tested, write exactly ONE dedicated logging test case. Never repeat it as a step in other test cases.

MANDATORY OUTPUT RULES:
- TEST CASE ORDER — always generate in this sequence:
  1. Primary positive functional cases first (the core happy path scenarios)
  2. Boundary and edge cases
  3. Negative cases (invalid input, error states, blocked access)
  4. @Lang cases LAST — they are supplementary coverage, never the lead test case
  @Lang cases must NEVER appear as test case #1, #2, or #3. They follow after all functional cases are complete.
- @Lang COVERAGE — for any frontend/UI requirement: ALL 4 @Lang cases MUST be present somewhere in your output: @Lang Regional Script, @Lang Bilingual, @Lang Mixed Script, @Lang Input Search. Missing even one is invalid. But they come AFTER functional cases.
- @Lang cases test LANGUAGE RENDERING of the primary feature — they are not general language tests. Each @Lang step must verify the PRIMARY TEST SUBJECT's behaviour in that language context, not just "text is displayed".
- Browser mention: maximum ONCE, at step 1 only, and ONLY when layout/rendering is the specific thing being tested. Omit entirely for functional tests.
- Step 1 for search/browse flows: use the actual platform name when known — web → "Open the website", touch → "Open the mobile site", android app → "Open the Android app", ios app → "Open the iOS app". Say "Open the platform URL" ONLY when platform is unknown. NEVER say "Open the B2B homepage".
- Step 1 for authenticated flows: "Login with valid credentials and navigate to [specific section]".
- Each step = one action + its expected outcome. No standalone navigation steps without a verification.
- NEVER write placeholder steps. Every step must be specific to this exact requirement.
- SLA / response time checks (e.g. "within 5 seconds"): if the requirement explicitly states an SLA, generate EXACTLY ONE dedicated performance test case for it. NEVER embed SLA checks as a step inside a functional test case — it is a separate concern.
- Security/privacy checks (PII, confidential data, data masking, sensitive info exposure):
  • For CRITICAL flows (payments, KYC, financial transactions, OTP/authentication, contract data): embed the security check as a step within the same test case — it is inherently part of the flow.
  • For NON-CRITICAL flows (general search, chatbot responses, listing display): security checks are a SEPARATE dedicated test case, not an embedded step. Do not add "verify no confidential info" as a step inside a search or chatbot functional test.

PLATFORM DOMAIN GLOSSARY — know these terms before generating:
- "Hotkey": A category-specific shortcut icon/thumbnail displayed on the platform homepage. Each hotkey represents a vertical (e.g. Movies, Vehicles, Restaurants). Tapping a hotkey is the ENTRY POINT — it either opens a pre-filtered search results/listing page for that vertical OR initiates that vertical's search flow directly. Hotkeys are NOT typed keywords. Test steps must reflect a TAP action on an icon, NOT a text search. The E2E flow is: Homepage → Tap hotkey icon → Vertical listing/filter page loads → User interacts with listings → Navigates to details page → Back navigation restores state.
- "Vertical": A specific business category/domain within the platform (e.g. Movies, Auto, Real Estate, Jobs). Verticals have dedicated pages, filters, and listing formats.
- "PRP" (Product/Provider Result Page): The B2B search result page. Always reached via category search, never direct URL. Vehicle type section appears below city name.
- "PDP" (Product/Provider Details Page): The business details page. Reached by tapping a listing on PRP or company name search.
- "VN" (Virtual Number): A tracked phone number shown to paid clients. PLATFORM SCOPE IS CRITICAL:
  • Web (desktop) ONLY: VN is shown via the "Show Number" button. Do NOT generate Show Number test cases for touch or app platforms.
  • Touch / App: VN is NOT shown via Show Number button — different mechanism applies on those platforms.
  VN appears on MULTIPLE web pages — result page, PRP, PDP, catalogue page, and details page. Cover all applicable web pages unless the requirement restricts to one. Apply the universal count-based display rule: 0 numbers → button absent or disabled; 1 number → inline, no panel; 2+ numbers → panel/div below button; many → scrollable panel. Each number must be a valid Indian phone number.
- "DVN" (Dynamic Virtual Number): A rotating tracked number for non-paid clients. Rotates on cache clear, session expiry, or TTL.

Each test case must include an "examples" field. Pick the correct type — (A) search/filter/booking: 3–5 real city+category+brand input combos; (B) flow/sync/auth/permissions/campaign: scenario condition labels e.g. "Account: Professional | FB Page: Linked | Campaign: Active"; (C) @Lang or pure UI/visual: empty string ""; (D) API/backend: method + key payload fields + auth state + expected HTTP status e.g. "POST /sync | token: valid | account_type: professional → 200 OK". Never use city/brand combos for workflow or API tests.
Steps must be short and direct — active voice, under 20 words each, no filler preamble.
Return STRICT JSON only: {"positive_tests": [{"title": "", "steps": [], "examples": ""}], "negative_tests": [{"title": "", "steps": [], "examples": ""}]}"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def _encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """Returns (base64_data, media_type)."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(suffix, "image/png")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


_REASONING_MODELS = {"o1", "o3", "o4-mini", "o1-mini", "o1-preview"}

def ask_ai(
    prompt: str,
    strict_mode: bool = False,
    expect_json: bool = True,
    system_prompt: str = None
) -> str:
    """
    Central AI invocation layer.
    Supports:
    - o3 / reasoning models (no temperature, uses reasoning_effort)
    - JSON enforcement
    - Custom system prompt (pass hard rules here for maximum compliance)
    - Error resilience
    """

    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    is_reasoning = model in _REASONING_MODELS

    # Allow scaling output size via env; keep safe defaults.
    max_tokens_env = os.getenv("AI_MAX_TOKENS", "12000")
    try:
        max_tokens = int(max_tokens_env)
    except ValueError:
        max_tokens = 12000
    max_tokens = max(1000, min(max_tokens, 100000))

    default_system = (
        "You are a senior QA architect with strong "
        "focus on structured, deterministic output."
    )

    kwargs = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "response_format": {"type": "json_object"} if expect_json else None,
        "messages": [
            {
                "role": "system",
                "content": system_prompt if system_prompt else default_system
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    if not is_reasoning:
        # Reasoning models don't accept temperature
        kwargs["temperature"] = 0.3 if strict_mode else 0.6

    try:
        response = _get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    except Exception as e:
        print("AI SERVICE ERROR:", str(e))
        raise RuntimeError("AI generation failed.")


def ask_ai_with_image(image_path: str, prompt: str, expect_json: bool = True) -> str:
    """
    Vision-capable AI call using GPT-4o.
    Accepts a local image file path + a text prompt.
    Returns the model response as a string.
    """
    suffix = Path(image_path).suffix.lower()
    if suffix not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {suffix}. Allowed: {ALLOWED_IMAGE_TYPES}")

    b64_data, media_type = _encode_image_to_base64(image_path)
    data_url = f"data:{media_type};base64,{b64_data}"

    max_tokens_env = os.getenv("AI_MAX_TOKENS", "7000")
    try:
        max_tokens = int(max_tokens_env)
    except ValueError:
        max_tokens = 7000
    max_tokens = max(1000, min(max_tokens, 12000))

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior QA architect with 12+ years of experience. "
                    "You specialize in analysing UI screenshots, mockups, and design files "
                    "to produce structured, production-level test cases."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        kwargs = {
            "model": "gpt-4o",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        # json_object response_format is not supported on vision calls in all regions;
        # rely on prompt-level instruction + post-parse instead.
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = _get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    except Exception as e:
        print("AI VISION SERVICE ERROR:", str(e))
        raise RuntimeError(f"Image-based AI generation failed: {e}")
