import json
from echuu.core.persona_expander import PersonaExpander
from echuu.core.persona_dossier import CharacterDossier


class FakeLLM:
    def __init__(self, payload):
        self._payload = payload
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._payload


class BoomLLM:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("api down")


_GOOD = json.dumps({
    "expanded_bio": "她表面温柔，其实一直在替所有人兜底，开始有点恨这一点。",
    "conflict": {"angle": "反面", "premise": "她很温柔",
                 "statement": "她从不拒绝别人，但心里在记账"},
    "behavior_rules": {
        "avoid_topics": ["直接拒绝别人"],
        "trigger": "被要求帮忙 → 先答应，然后停顿+自嘲",
        "contradiction": "嘴上说没事，行为在拖延",
        "breaking_point": "被第三次索取会突然强硬，然后立刻道歉",
    },
}, ensure_ascii=False)


def test_expand_parses_llm_json():
    llm = FakeLLM(_GOOD)
    d = PersonaExpander().expand("小柔", "很温柔的邻家女孩", "", None, llm)
    assert isinstance(d, CharacterDossier)
    assert d.conflict.statement == "她从不拒绝别人，但心里在记账"
    assert d.behavior_rules.breaking_point.startswith("被第三次索取")


def test_premise_traceable_to_input_in_prompt():
    llm = FakeLLM(_GOOD)
    PersonaExpander().expand("小柔", "很温柔的邻家女孩", "", None, llm)
    # 用户输入必须进 prompt（冲突长在输入上，可追溯）
    assert "很温柔的邻家女孩" in llm.prompts[0]
    # 四角度必须在指令里
    assert "代价" in llm.prompts[0] and "反面" in llm.prompts[0]


def test_degrades_without_crash():
    d = PersonaExpander().expand("小柔", "很温柔", "", None, BoomLLM())
    assert isinstance(d, CharacterDossier)
    assert d.conflict.statement  # 非空兜底
    assert not d.is_empty()


def test_bad_json_degrades():
    d = PersonaExpander().expand("x", "y", "", None, FakeLLM("not json at all"))
    assert d.conflict.statement
