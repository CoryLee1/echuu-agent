from echuu.core.prompt_leakage import find_prompt_leaks


def test_detects_internal_marker_in_audience_text():
    leaks = find_prompt_leaks({
        "units": [{"lines": [{"text": "先把已经确认的事实摆出来，再回答。"}]}],
    })
    assert "先把已经确认的事实摆出来" in leaks


def test_detects_long_annotator_rule_fragment():
    guidance = [{
        "category": "style",
        "rule": "每一句都必须围绕同一个中心推进，不能展示内部调整过程。",
    }]
    leaks = find_prompt_leaks(
        "每一句都必须围绕同一个中心推进，不能展示内部调整过程。",
        guidance,
    )
    assert leaks


def test_ignores_structured_field_names_when_not_spoken():
    assert not find_prompt_leaks({
        "spine_link": "把答案继续吊到最后",
        "purpose": "接住玩笑",
        "lines": [{"text": "Okay，我差点就说出来了。"}],
    })


def test_detects_compact_repair_protocol_echo():
    leaks = find_prompt_leaks({
        "lines": [{"text": "CONTRACT=... silent_quality_checks 必须全部通过"}],
    })
    assert "CONTRACT=" in leaks
    assert "silent_quality_checks" in leaks
