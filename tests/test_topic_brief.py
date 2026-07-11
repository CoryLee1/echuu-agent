"""主题语义 grounding：联网检索主题真实含义，注入 background。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echuu.modes.topic_brief import produce_topic_brief, merge_brief_into_background


class SearchLLM:
    def __init__(self, answer="云养猫指自己不养猫，通过刷猫视频、追猫博主获得养猫体验。"):
        self.answer = answer
        self.prompts = []

    def call_with_search(self, prompt, system=None, max_tokens=0):
        self.prompts.append(prompt)
        return self.answer


class PlainLLM:
    """没有 call_with_search 的 provider（Claude/Gemini）。"""

    def call(self, prompt, max_tokens=0):
        return "should not be used"


def test_brief_uses_search_call():
    llm = SearchLLM()
    brief = produce_topic_brief(llm, "云养猫")
    assert "刷猫视频" in brief
    assert "云养猫" in llm.prompts[0]


def test_brief_skips_provider_without_search():
    assert produce_topic_brief(PlainLLM(), "云养猫") == ""


def test_brief_empty_topic():
    assert produce_topic_brief(SearchLLM(), "") == ""


def test_brief_search_failure_degrades_to_empty():
    class Broken:
        def call_with_search(self, prompt, system=None, max_tokens=0):
            raise RuntimeError("network down")

    assert produce_topic_brief(Broken(), "云养猫") == ""


def test_merge_brief_into_background():
    merged = merge_brief_into_background("原有背景", "云养猫", "真实含义……")
    assert "原有背景" in merged
    assert "真实含义" in merged
    # 空 brief 不改动 background
    assert merge_brief_into_background("原有背景", "云养猫", "") == "原有背景"
    # 空 background 也能独立成段
    assert "真实含义" in merge_brief_into_background("", "云养猫", "真实含义……")
