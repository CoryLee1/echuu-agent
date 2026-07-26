"""Compile TRAIN annotations into bounded, generalized generation rules."""
from __future__ import annotations

import re
from typing import Any, Iterable


_FALLBACK_RULES = {
    "world_knowledge": (
        "涉及教育、医疗、法律或职业制度时，只陈述输入支持的事实；信息不足时使用中性表达，"
        "不要把类比写成真实制度。"
    ),
    "fabricated_detail": (
        "不得补造日期、数量、身体特征、伤病、私人物件或人物履历；具体感优先来自当下可观察动作。"
    ),
    "focus_drift": (
        "每段必须直接推进唯一主轴；删掉后不影响结论的段落应删除或合并。"
    ),
    "logic": (
        "省略、转折和因果句必须语义完整，明确交代主语、结果与判断依据，不能用破折号掩盖信息缺口。"
    ),
    "persona": "只使用用户明确提供的人设事实；模型扩充内容只能作为表达假设，不能升级成人物履历。",
    "repetition": "同一具体数字、事实或结论全篇只说一次；再次出现必须增加新信息，否则删除。",
    "style": "优先自然口语和清晰表达，不为追求金句堆叠隐喻、数字或戏剧化细节。",
    "safety": "不确定的高风险事实使用审慎、中性表达，不给出无依据的确定性判断。",
    "other": "按批注指出的可泛化质量问题修正，但不得复制被批注原句或针对单一样本写特例。",
}

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
_ACTIVE_STATUSES = {"planned", "applied", "validated"}


def _source_fixture_id(run_id: str) -> str:
    return str(run_id or "").split("__r", 1)[0]


def _infer_category(note: dict[str, Any]) -> str:
    category = str(note.get("category", "")).strip()
    if category:
        return category
    text = " ".join(str(note.get(key, "")) for key in ("adjustment", "issue_feedback"))
    if any(term in text for term in ("硬事实", "日期", "身体特征", "伤疤", "捏造")):
        return "fabricated_detail"
    return "other"


def _clean_demo_prefix(value: Any) -> str:
    return re.sub(r"^【演示】\s*", "", str(value or "").strip())


def compile_tuning_guidance(
    notes: Iterable[dict[str, Any]],
    train_fixture_ids: Iterable[str],
    limit: int = 8,
) -> list[dict[str, str]]:
    """Use generalized fixes from TRAIN only; never leak quoted target text."""
    train_ids = set(train_fixture_ids)
    candidates: list[tuple[int, str, dict[str, str]]] = []
    seen: set[tuple[str, str]] = set()
    for note in notes:
        if not isinstance(note, dict):
            continue
        if _source_fixture_id(str(note.get("run_id", ""))) not in train_ids:
            continue
        if str(note.get("status", "planned")) not in _ACTIVE_STATUSES:
            continue
        feedback_type = str(note.get("feedback_type", "mixed"))
        category = _infer_category(note)
        if feedback_type == "positive" or category == "strength":
            continue
        adjustment = _clean_demo_prefix(note.get("adjustment", ""))
        rule = adjustment or _FALLBACK_RULES.get(category, _FALLBACK_RULES["other"])
        key = (category, rule)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((
            _SEVERITY_RANK.get(str(note.get("severity", "medium")), 1),
            str(note.get("created_at", "")),
            {
                "id": str(note.get("id", "")).strip(),
                "category": category,
                "rule": rule,
                "expected_effect": _clean_demo_prefix(note.get("expected_effect", "")),
            },
        ))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in candidates[:max(0, limit)]]
