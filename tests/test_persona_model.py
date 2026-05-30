"""Tests for PersonaModel — three-axis extraction + degradation."""
from __future__ import annotations

import json
import pytest

from echuu.core.persona_model import PersonaModel


class FakeLLM:
    """Minimal stub matching the .generate(prompt: str) -> str shape."""
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


def test_from_persona_text_happy_path():
    llm = FakeLLM(json.dumps({
        "identity": "25 岁前 HR，现自由插画师",
        "belief": "做喜欢的事比薪水重要",
        "flaw": "决定辞职那天还是哭了一整夜",
        "visual_anchor": "腕上贴满便签的滑稽手账",
        "title_hook": "我跟你讲，从 HR 转行插画师那天我把所有便签都贴在手上了——",
    }))
    pm = PersonaModel.from_persona_text("我是 25 岁前 HR ...", llm)
    assert pm.identity == "25 岁前 HR，现自由插画师"
    assert pm.belief
    assert pm.flaw
    assert pm.visual_anchor
    assert pm.title_hook
    assert pm.flaw is not None  # I4


def test_from_persona_text_invalid_json_falls_back():
    llm = FakeLLM("not valid json at all {{{")
    pm = PersonaModel.from_persona_text("一段 persona 文本", llm)
    # 重试一次后仍失败 → 退化路径
    assert pm.identity.startswith("一段 persona 文本") or "[" in pm.identity
    # flaw 必须非 None / 非空（I4）
    assert pm.flaw
    assert pm.flaw is not None
    assert pm.visual_anchor
    assert pm.title_hook


def test_from_persona_text_missing_flaw_falls_back():
    """LLM 返回合法 JSON 但缺 flaw 字段 → 整体退化路径，确保 flaw 有占位。"""
    llm = FakeLLM(json.dumps({
        "identity": "A",
        "belief": "B",
        # flaw 缺失
        "visual_anchor": "D",
        "title_hook": "E",
    }))
    pm = PersonaModel.from_persona_text("p", llm)
    assert pm.flaw
    # 因为缺字段被判为不合法，进入占位路径
    assert "[" in pm.flaw or pm.flaw != ""


def test_from_persona_text_strips_code_fences():
    """LLM 包了 ```json ... ``` 也能解析。"""
    payload = json.dumps({
        "identity": "X", "belief": "Y", "flaw": "Z",
        "visual_anchor": "V", "title_hook": "T",
    })
    llm = FakeLLM(f"```json\n{payload}\n```")
    pm = PersonaModel.from_persona_text("p", llm)
    assert pm.identity == "X"
    assert pm.flaw == "Z"


def test_persona_model_is_frozen():
    """PersonaModel 一次抽完锁定全程不变（spec §2.3）。"""
    pm = PersonaModel(identity="a", belief="b", flaw="c", visual_anchor="d", title_hook="e")
    with pytest.raises(Exception):
        pm.identity = "changed"  # type: ignore
