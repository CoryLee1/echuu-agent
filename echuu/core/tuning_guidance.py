"""Shared helpers for applying human evaluation notes without copying examples."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


def normalize_tuning_guidance(value: Any) -> tuple[dict[str, str], ...]:
    """Keep only the small, generalized rule payload accepted by generators."""
    if not isinstance(value, (list, tuple)):
        return ()
    rules: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rule = str(item.get("rule", "")).strip()
        if not rule:
            continue
        rules.append({
            "id": str(item.get("id", "")).strip(),
            "category": str(item.get("category", "other")).strip() or "other",
            "rule": rule,
            "expected_effect": str(item.get("expected_effect", "")).strip(),
        })
    return tuple(rules)


def render_tuning_guidance(value: Any) -> str:
    """Render rules only—never excerpts, observations, or annotator wording."""
    rules = normalize_tuning_guidance(value)
    if not rules:
        return ""
    return "\n".join(
        f"{index}. [{item['category']}] {item['rule']}"
        for index, item in enumerate(rules, start=1)
    )


_GENERATION_FLAGS = {
    "world_knowledge": "domain_grounding",
    "fabricated_detail": "fact_grounding",
    "focus_drift": "single_spine",
    "logic": "clause_completeness",
    "persona": "persona_grounding",
    "repetition": "avoid_repetition",
    "style": "natural_style",
    "safety": "risk_calibration",
}
_STAGE_FLAGS = {
    "dossier": {"fact_grounding", "persona_grounding", "risk_calibration"},
    "analyst": {
        "domain_grounding", "fact_grounding", "single_spine",
        "clause_completeness", "persona_grounding", "natural_style",
        "risk_calibration",
    },
    "writer": set(_GENERATION_FLAGS.values()),
}


def render_generation_constraints(value: Any, stage: str) -> str:
    """Render bounded machine flags, never annotator-written natural language."""
    allowed = _STAGE_FLAGS.get(stage, set(_GENERATION_FLAGS.values()))
    flags = sorted({
        _GENERATION_FLAGS.get(item["category"], "")
        for item in normalize_tuning_guidance(value)
    }.intersection(allowed))
    if not flags:
        return ""
    return json.dumps(
        {"silent_quality_checks": flags},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def tuning_guidance_fingerprint(value: Any) -> str:
    rendered = render_tuning_guidance(value)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:16] if rendered else ""


def tuning_guidance_ids(value: Any) -> list[str]:
    return [item["id"] for item in normalize_tuning_guidance(value) if item["id"]]


def tuning_guidance_categories(value: Any) -> list[str]:
    return list(dict.fromkeys(
        item["category"] for item in normalize_tuning_guidance(value)
    ))
