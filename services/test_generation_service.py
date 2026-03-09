import json
import re
from typing import Dict, Optional
from dotenv import load_dotenv
from ai_service import ask_ai
from testcase_generator import generate_testcases

load_dotenv()

# -----------------------------
# CONFIGURATION
# -----------------------------

ALL_LAYERS = [
    "ui",
    "validation",
    "state",
    "api",
    "security",
    "performance",
    "cross_browser"
]

LAYER_KEYWORDS = {
    "ui": ["ui", "ux", "design", "layout", "frontend", "front-end", "front end", "display", "popup", "alert", "warning", "pop up", "modal"],
    "api": ["api", "endpoint", "service"],
    "security": ["security", "auth", "authentication", "authorization", "encryption"],
    "performance": ["performance", "latency", "response time", "load", "throughput"],
    "state": [
        "state",
        "session",
        "resume",
        "relaunch",
        "last searched",
        "last visited",
        "restore",
    ],
    "cross_browser": ["cross browser", "browser compatibility", "all browsers"],
    "validation": ["validation", "validate", "function", "functional", "verify", "check", "business rule", "business logic"],
}

STRICT_PATTERN = re.compile(r"^\s*ps-only\s+(.+)", re.IGNORECASE)
STRICT_GENERIC_VALIDATION_VERBS = {"verify", "validate", "check"}

# -------------------------------------------------
# CLASSIFICATION ENGINE (Deterministic)
# -------------------------------------------------

def classify_requirement(requirement: str) -> Dict:
    text = requirement.lower()

    classification = {
        "mode": "inferred",
        "type": "unknown",
        "include_layers": [],
        "exclude_layers": [],
        "confidence": 0.0
    }

    # ---------- STRICT MODE ----------
    strict_match = STRICT_PATTERN.match(requirement)

    if strict_match:
        classification["mode"] = "strict"
        strict_scope_text = strict_match.group(1).lower()

        included_layers = []

        for layer, keywords in LAYER_KEYWORDS.items():
            for keyword in keywords:
                if (
                    layer == "validation"
                    and keyword in STRICT_GENERIC_VALIDATION_VERBS
                ):
                    # In strict mode, generic verbs should not expand scope.
                    continue
                if re.search(rf"\b{re.escape(keyword)}\b", strict_scope_text):
                    included_layers.append(layer)
                    break

        if not included_layers:
            classification["type"] = "invalid_scope"
            classification["confidence"] = 0.0
            classification["error"] = "PS-ONLY requires explicit valid layer."
            return classification

        classification["include_layers"] = sorted(set(included_layers))
        classification["exclude_layers"] = [
            layer for layer in ALL_LAYERS
            if layer not in classification["include_layers"]
        ]

        classification["type"] = (
            classification["include_layers"][0]
            if len(classification["include_layers"]) == 1
            else "multi_scope"
        )

        classification["confidence"] = 1.0
        return classification

    # ---------- INFERRED MODE ----------

    layer_scores = {layer: 0 for layer in LAYER_KEYWORDS.keys()}

    for layer, keywords in LAYER_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                layer_scores[layer] += 1

    matched_layers = [layer for layer, score in layer_scores.items() if score > 0]

    if not matched_layers:
        classification["confidence"] = 0.2
        return classification

    classification["include_layers"] = matched_layers
    classification["exclude_layers"] = [
        layer for layer in ALL_LAYERS
        if layer not in matched_layers
    ]

    classification["type"] = (
        matched_layers[0]
        if len(matched_layers) == 1
        else "multi_scope"
    )

    total_matches = sum(layer_scores.values())
    classification["confidence"] = min(0.95, 0.5 + (0.1 * total_matches))

    return classification


# -------------------------------------------------
# AI STRUCTURED ANALYSIS
# -------------------------------------------------

def analyze_requirement(requirement: str) -> Dict:

    classification = classify_requirement(requirement)

    prompt = f"""
You are a senior QA architect.

System Classification (deterministic engine result):
{json.dumps(classification, indent=2)}

Analyze the requirement and extract structured system understanding.

Return ONLY valid JSON.

Format:
{{
  "feature": "",
  "actors": [],
  "inputs": [],
  "constraints": [],
  "business_rules": [],
  "possible_apis": []
}}

Requirement:
{requirement}
"""

    try:
        content = ask_ai(
            prompt,
            strict_mode=True,
            expect_json=True
        )
    except Exception:
        content = None

    structured_output = _safe_parse_json_object(content)

    if structured_output is None:
        structured_output = {
            "feature": requirement.strip(),
            "actors": [],
            "inputs": [],
            "constraints": [],
            "business_rules": [],
            "possible_apis": []
        }
        structured_output["_analysis_error"] = "AI analysis failed or returned invalid JSON."

    # Inject classification safely (backward compatible)
    structured_output["_classification"] = classification

    return structured_output


def _safe_parse_json_object(content: Optional[str]) -> Optional[Dict]:
    if not content:
        return None

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None


# -------------------------------------------------
# TEST SUITE GENERATION WRAPPER
# -------------------------------------------------

def generate_full_test_suite(
    request,
    existing_cases: Optional[list] = None,
    update_comment: Optional[str] = None
):
    """
    Wrapper to analyze requirement and generate testcases.
    """

    analysis = analyze_requirement(request.requirement)

    # Preserve original requirement text so generate_testcases can use
    # it for keyword detection and as the authoritative prompt content.
    # analysis["feature"] is only a short AI-extracted name — not the full text.
    analysis["_original_requirement"] = request.requirement

    def _enum_or_value(items):
        values = []
        for item in items or []:
            values.append(item.value if hasattr(item, "value") else item)
        return values

    analysis["platforms"] = _enum_or_value(request.platforms)
    analysis["modules"] = _enum_or_value(request.modules)
    analysis["pages"] = _enum_or_value(request.pages)
    analysis["test_types"] = _enum_or_value(request.test_types)
    analysis["self_learning"] = request.enable_self_learning
    analysis["third_party_learning"] = request.learn_from_third_party

    # If this request originated from image analysis, merge the vision-extracted
    # business rules and constraints into the analysis so the generator uses them.
    image_analysis = getattr(request, "_image_analysis", None)
    if image_analysis and isinstance(image_analysis, dict):
        existing_rules = analysis.get("business_rules") or []
        vision_rules = image_analysis.get("business_rules") or []
        # Merge without duplicates, vision rules take priority
        merged_rules = vision_rules + [r for r in existing_rules if r not in vision_rules]
        analysis["business_rules"] = merged_rules

        existing_constraints = analysis.get("constraints") or []
        vision_constraints = image_analysis.get("constraints") or []
        merged_constraints = vision_constraints + [c for c in existing_constraints if c not in vision_constraints]
        analysis["constraints"] = merged_constraints

        # Use vision-extracted feature name if the AI analysis produced a generic one
        if image_analysis.get("feature") and not analysis.get("feature"):
            analysis["feature"] = image_analysis["feature"]

    return generate_testcases(
        analysis,
        existing_cases=existing_cases,
        update_comment=update_comment
    )
