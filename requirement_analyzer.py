import os
import json
import re
from typing import Dict, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        _client = OpenAI(api_key=api_key)
    return _client

# -----------------------------
# CONFIGURATION (Extensible)
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
    "ui": ["ui", "ux", "design", "layout"],
    "api": ["api", "endpoint", "service"],
    "security": ["security", "auth", "authentication", "authorization", "encryption"],
    "performance": ["performance", "latency", "response time", "load", "throughput"],
    "state": ["state", "state management", "session"],
    "cross_browser": ["cross browser", "browser compatibility", "all browsers"],
}

STRICT_PATTERN = re.compile(
    r"^\s*ps-only\s+(.+)",
    re.IGNORECASE
)


# -----------------------------
# CLASSIFICATION ENGINE
# -----------------------------

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
                if re.search(rf"\b{re.escape(keyword)}\b", strict_scope_text):
                    included_layers.append(layer)
                    break

        if not included_layers:
            classification["type"] = "invalid_scope"
            classification["confidence"] = 0.0
            classification["error"] = "PS-ONLY requires explicit valid layer."
            return classification

        classification["include_layers"] = sorted(list(set(included_layers)))
        classification["exclude_layers"] = [
            layer for layer in ALL_LAYERS if layer not in classification["include_layers"]
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
        layer for layer in ALL_LAYERS if layer not in matched_layers
    ]

    if len(matched_layers) == 1:
        classification["type"] = matched_layers[0]
    else:
        classification["type"] = "multi_scope"

    total_matches = sum(layer_scores.values())
    classification["confidence"] = min(0.95, 0.5 + (0.1 * total_matches))

    return classification


# -----------------------------
# AI ANALYSIS
# -----------------------------

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

    response = _get_client().chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content
    structured_output = json.loads(content)

    return {
        "classification": classification,
        "analysis": structured_output
    }