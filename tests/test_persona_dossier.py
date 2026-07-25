from echuu.core.persona_dossier import Conflict, BehaviorRules, CharacterDossier


def _sample() -> CharacterDossier:
    return CharacterDossier(
        expanded_bio="她表面温柔，其实一直在替所有人兜底。",
        conflict=Conflict(angle="反面", premise="她很温柔",
                          statement="她从不拒绝别人，但心里在记账"),
        behavior_rules=BehaviorRules(
            avoid_topics=("直接拒绝别人", "承认自己累"),
            trigger="被要求帮忙 → 先答应，然后停顿+自嘲",
            contradiction="嘴上说没事，行为在拖延",
            breaking_point="被第三次索取会突然强硬，然后立刻道歉",
        ),
    )


def test_from_dict_roundtrip():
    d = _sample()
    data = {
        "expanded_bio": d.expanded_bio,
        "conflict": {"angle": "反面", "premise": "她很温柔",
                     "statement": "她从不拒绝别人，但心里在记账"},
        "behavior_rules": {
            "avoid_topics": ["直接拒绝别人", "承认自己累"],
            "trigger": "被要求帮忙 → 先答应，然后停顿+自嘲",
            "contradiction": "嘴上说没事，行为在拖延",
            "breaking_point": "被第三次索取会突然强硬，然后立刻道歉",
        },
    }
    got = CharacterDossier.from_dict(data)
    assert got == d


def test_from_dict_none_and_empty():
    assert CharacterDossier.from_dict(None) is None
    assert CharacterDossier.from_dict({}) is None
    assert CharacterDossier.from_dict({"conflict": {}, "behavior_rules": {}}) is None


def test_from_dict_nondict_nested_degrades():
    # Non-dict values in conflict/behavior_rules must not crash (degrade gracefully)
    assert CharacterDossier.from_dict({"conflict": "not-a-dict"}) is None
    assert CharacterDossier.from_dict({"behavior_rules": ["a", "b"]}) is None
    # Valid data alongside bad behavior_rules still parses, no crash
    d = CharacterDossier.from_dict({
        "conflict": {"statement": "x"},
        "behavior_rules": "bad"
    })
    assert d is not None and d.conflict.statement == "x"
    # Bad conflict with valid behavior_rules
    d = CharacterDossier.from_dict({
        "conflict": 123,
        "behavior_rules": {"trigger": "y"}
    })
    assert d is not None and d.behavior_rules.trigger == "y"


def test_render_lists_only_nonempty():
    text = _sample().render_for_prompt()
    assert "她从不拒绝别人，但心里在记账" in text
    assert "嘴上说没事，行为在拖延" in text
    assert "被第三次索取" in text
    # 空字段不渲染标签
    empty = CharacterDossier(
        expanded_bio="",
        conflict=Conflict(angle="", premise="", statement="只有这一句"),
        behavior_rules=BehaviorRules(avoid_topics=(), trigger="", contradiction="", breaking_point=""),
    )
    et = empty.render_for_prompt()
    assert "只有这一句" in et
    assert "回避" not in et and "爆发点" not in et
