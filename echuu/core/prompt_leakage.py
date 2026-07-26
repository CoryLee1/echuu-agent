"""Detect internal prompt/rubric text that must never reach audience-facing copy."""
from __future__ import annotations

import re
from typing import Any, Iterable


INTERNAL_PROMPT_MARKERS = (
    "spine_link",
    "supporting_points",
    "tuning_guidance",
    "fact_grounding",
    "domain_grounding",
    "clause_completeness",
    "single_spine",
    "avoid_repetition",
    "natural_style",
    "已批准的人类调教规则",
    "TRAIN 批注",
    "自动质量守门",
    "只输出规定 JSON",
    "事实守门",
    "删段测试",
    "可当作事实的原始输入",
    "模型整理或假设",
    "唯一事实来源",
    "本轮内容合同",
    "节奏分段",
    "生成约束",
    "单核心写作契约",
    "静默质量标志",
    "静默质量检查",
    "内部检查",
    "不得在输出中提及",
    "只输出 JSON",
    "只输出JSON",
    "CONTRACT=",
    "SOURCE=",
    "PREVIOUS=",
    "FORBIDDEN_OUTPUT_FRAGMENTS=",
    "silent_quality_checks",
    "unit_count",
    "prompt_version",
    "quality_gate",
    "planted_gags",
    "lines.text",
    "先把已经确认的事实摆出来",
    "判断重点是现在还能不能获得有效支持",
    "核实真实流程、成果安排",
    "支持、流程和实际代价",
)


def _string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _string_values(item)
    elif hasattr(value, "__dataclass_fields__"):
        for field_name in value.__dataclass_fields__:
            yield from _string_values(getattr(value, field_name, None))


def _guidance_fragments(tuning_guidance: Any) -> set[str]:
    fragments: set[str] = set()
    for item in tuning_guidance or ():
        if not isinstance(item, dict):
            continue
        rule = str(item.get("rule", "")).strip()
        for clause in re.split(r"[。！？；;\n]+", rule):
            clause = clause.strip()
            if len(clause) >= 10:
                fragments.add(clause)
    return fragments


def find_prompt_leaks(
    value: Any,
    tuning_guidance: Any = None,
) -> tuple[str, ...]:
    """Return exact internal markers/rule clauses found in output string values."""
    text = "\n".join(_string_values(value))
    markers = set(INTERNAL_PROMPT_MARKERS)
    markers.update(_guidance_fragments(tuning_guidance))
    return tuple(sorted(
        (marker for marker in markers if marker and marker in text),
        key=lambda marker: (-len(marker), marker),
    ))
