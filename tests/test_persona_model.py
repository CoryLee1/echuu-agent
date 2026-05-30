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
