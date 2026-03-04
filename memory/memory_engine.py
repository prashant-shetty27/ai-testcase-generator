import json
import os
import hashlib
from datetime import datetime

MEMORY_FILE = "memory_store.json"


# -----------------------------
# UTILITIES
# -----------------------------

def _load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _generate_fingerprint(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode()).hexdigest()


# -----------------------------
# PUBLIC API (UNCHANGED)
# -----------------------------

def get_patterns_for_requirement(requirement: str):
    memory = _load_memory()
    entry = memory.get(requirement)
    if not entry:
        return []
    return entry.get("scenarios", [])


def store_patterns(requirement: str, testcases: dict):
    memory = _load_memory()

    if requirement not in memory:
        memory[requirement] = {
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "scenarios": [],
            "fingerprints": [],
            "stats": {
                "total_cases": 0,
                "positive_cases": 0,
                "negative_cases": 0,
                "high_priority": 0
            },
            "reinforcement": {}
        }

    entry = memory[requirement]

    positive = testcases.get("positive_tests", [])
    negative = testcases.get("negative_tests", [])
    all_cases = positive + negative

    new_cases = []
    duplicate_count = 0

    for case in all_cases:
        scenario = case.get("scenario", "")
        if not scenario:
            continue

        fingerprint = _generate_fingerprint(scenario)

        if fingerprint not in entry["fingerprints"]:
            entry["scenarios"].append(case)
            entry["fingerprints"].append(fingerprint)
            new_cases.append(case)

            entry["stats"]["total_cases"] += 1

            if case in positive:
                entry["stats"]["positive_cases"] += 1
            else:
                entry["stats"]["negative_cases"] += 1

            if case.get("priority", "").lower() == "high":
                entry["stats"]["high_priority"] += 1
        else:
            duplicate_count += 1

    # -----------------------------
    # REINFORCEMENT SCORING
    # -----------------------------

    reinforcement_score = _calculate_reinforcement_score(
        new_cases,
        duplicate_count,
        len(all_cases)
    )

    entry["reinforcement"] = reinforcement_score
    entry["last_updated"] = datetime.utcnow().isoformat()

    _save_memory(memory)


# -----------------------------
# REINFORCEMENT LOGIC
# -----------------------------

def _calculate_reinforcement_score(new_cases, duplicate_count, total_cases):

    if total_cases == 0:
        return {}

    avg_steps = 0
    high_priority = 0
    negative_cases = 0

    for case in new_cases:
        steps = case.get("steps", [])
        avg_steps += len(steps)

        if case.get("priority", "").lower() == "high":
            high_priority += 1

        if "invalid" in case.get("scenario", "").lower() \
           or "error" in case.get("scenario", "").lower():
            negative_cases += 1

    avg_steps = avg_steps / len(new_cases) if new_cases else 0
    duplicate_ratio = duplicate_count / total_cases
    high_priority_ratio = high_priority / total_cases
    negative_ratio = negative_cases / total_cases

    # Weighted scoring logic
    score = (
        (avg_steps / 8) * 0.3 +
        (1 - duplicate_ratio) * 0.3 +
        high_priority_ratio * 0.2 +
        negative_ratio * 0.2
    )

    return {
        "avg_steps": round(avg_steps, 2),
        "duplicate_ratio": round(duplicate_ratio, 2),
        "high_priority_ratio": round(high_priority_ratio, 2),
        "negative_ratio": round(negative_ratio, 2),
        "score": round(score, 2)
    }