from echuu.core.tuning_guidance import (
    render_generation_constraints,
    render_tuning_guidance,
    tuning_guidance_fingerprint,
)
from echuu.eval.tuning_guidance import compile_tuning_guidance


def test_compile_uses_train_issue_rules_without_leaking_excerpt():
    notes = [
        {
            "id": "train-note",
            "run_id": "clip_001__r03",
            "status": "planned",
            "feedback_type": "issue",
            "category": "repetition",
            "severity": "high",
            "target_excerpt": "这句绝对不能泄漏",
            "adjustment": "",
        },
        {
            "id": "dev-note",
            "run_id": "clip_006__r01",
            "status": "applied",
            "feedback_type": "issue",
            "category": "style",
            "adjustment": "DEV 特例不能进入生成",
        },
        {
            "id": "positive-note",
            "run_id": "clip_001__r02",
            "status": "planned",
            "feedback_type": "positive",
            "category": "strength",
            "adjustment": "不应作为纠错规则",
        },
    ]

    rules = compile_tuning_guidance(notes, {"clip_001"})

    assert [rule["id"] for rule in rules] == ["train-note"]
    rendered = render_tuning_guidance(rules)
    assert "同一具体数字" in rendered
    assert "这句绝对不能泄漏" not in rendered
    assert tuning_guidance_fingerprint(rules)


def test_compile_prefers_generalized_adjustment():
    rules = compile_tuning_guidance([{
        "id": "n1",
        "run_id": "clip_001__r01",
        "status": "applied",
        "category": "world_knowledge",
        "adjustment": "涉及制度时先做领域常识校验。",
        "target_excerpt": "错误原句",
    }], {"clip_001"})

    assert rules[0]["rule"] == "涉及制度时先做领域常识校验。"
    assert "错误原句" not in str(rules)


def test_generation_constraints_use_flags_not_annotator_wording():
    rules = [{
        "id": "n1",
        "category": "world_knowledge",
        "rule": "这句人工调整原话绝不能进入生成 Prompt。",
    }]
    rendered = render_generation_constraints(rules, "writer")
    assert "domain_grounding" in rendered
    assert "人工调整原话" not in rendered
