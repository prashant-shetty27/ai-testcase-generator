import json
import uuid
from ai_service import ask_ai
from memory.memory_engine import get_patterns_for_requirement, store_patterns
from context_builder import build_context_block


def generate_testcases(analysis_json, existing_cases=None, update_comment=None):

    requirement = analysis_json.get("feature", "")
    test_types = analysis_json.get("test_types", [])

    platforms = analysis_json.get("platforms", [])
    modules = analysis_json.get("modules", [])
    pages = analysis_json.get("pages", [])

    classification = analysis_json.get("_classification", {})
    mode = classification.get("mode", "inferred")
    classified_type = classification.get("type", "unknown")
    confidence = classification.get("confidence", 0)

    memory_patterns = get_patterns_for_requirement(requirement)
    context_block = build_context_block(platforms, modules, pages, classification)

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
        kw in requirement.lower() for kw in notification_keywords
    )

    is_api_focus = (
        (mode == "strict" and "api" in classification.get("include_layers", []))
        or classified_type == "api"
        or is_notification_flow
    )

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
        else:
            e2e_block = """
If test type includes 'e2e':
Generate complete business workflow validation including:
- Search validation
- Filters (price, rating, location)
- Sorting
- Pagination
- Navigation to details page
- Data consistency checks
- Back navigation behavior
- Session persistence
- Mobile responsiveness
- Error handling
- Boundary conditions
- Browser compatibility
"""

    prompt = f"""
You are a Senior QA Architect with 12+ years of experience.

Requirement:
{requirement}

Platforms: {platforms}
Modules: {modules}
Pages: {pages}
Test Types: {test_types}

Classification:
Mode: {mode}
Type: {classified_type}
Confidence: {confidence}

{classification_guidance}

Previously learned important scenarios:
{memory_patterns}

Generate REALISTIC, production-level test cases.

{e2e_block}

    Each test case must:
    - Be business realistic
    - Be detailed
    - Have minimum 6 meaningful steps
    - Include validation checks
    - Include varied priorities (High/Medium/Low)
    - Have specific, observable expected results (manual tester style)
    - Avoid generic expected results like "should work correctly"

IMPORTANT CONTEXT:
{context_block}
- Currency must be INR (₹).
- Consider Indian GST, Indian cancellation policies if relevant.

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

        store_patterns(requirement, enforced)

        print("RAW AI OUTPUT:")
        print(ai_output)

        return enforced

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
            if not case.get("scenario"):
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
