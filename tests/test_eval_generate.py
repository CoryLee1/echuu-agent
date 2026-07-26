import json
from pathlib import Path
from echuu.eval.generate import render_script, generate_variant, stable_retrieval_seed


class _FakeEngine:
    """run() 产出两条 step 事件，setup 记录 enable_dossier。"""
    def __init__(self): self.enable, self.setup_kwargs = None, {}
    def setup(self, **kw):
        self.setup_kwargs = kw
        self.enable = kw.get("enable_dossier")
        return self
    def run(self, **kw):
        yield {"speech": "第一句"}
        yield {"speech": "第二句"}


class _FakeTTS:
    def synthesize(self, text): return b"RIFFfake"


def test_render_script_joins_speech():
    txt = render_script(_FakeEngine())
    assert txt == "第一句\n第二句"


def test_render_script_can_use_planned_lines_without_runtime_generation():
    class _Line:
        def __init__(self, text): self.text = text
    engine = _FakeEngine()
    engine.state = type("State", (), {"script_lines": [_Line("骨架扩写一"), _Line("骨架扩写二")]})()
    assert render_script(engine, script_only=True) == "骨架扩写一\n骨架扩写二"


def test_generate_variant_writes_text_and_audio(tmp_path: Path):
    fx = {"id": "c1", "topic": "帮朋友做决定", "human_transcript": "真人这么讲"}
    eng = _FakeEngine()
    res = generate_variant(fx, "with_dossier", str(tmp_path),
                           engine_factory=lambda: eng, tts=_FakeTTS())
    assert eng.enable is True
    assert res["variant"] == "with_dossier"
    assert (tmp_path / "c1" / "with_dossier" / "text.txt").read_text(encoding="utf-8") == "第一句\n第二句"
    assert (tmp_path / "c1" / "with_dossier" / "audio.wav").read_bytes() == b"RIFFfake"
    metadata = json.loads(
        (tmp_path / "c1" / "with_dossier" / "metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["variant"] == "with_dossier"
    assert metadata["source_fixture_id"] == "c1"
    trace = json.loads(
        (tmp_path / "c1" / "with_dossier" / "trace.json").read_text(encoding="utf-8")
    )
    assert trace["stages"][-1]["id"] == "tts"
    assert trace["stages"][-1]["metrics"]["audio_bytes"] == len(b"RIFFfake")


def test_generate_human_variant_uses_transcript(tmp_path: Path):
    fx = {"id": "c1", "topic": "t", "human_transcript": "真人这么讲"}
    res = generate_variant(fx, "human", str(tmp_path),
                           engine_factory=lambda: _FakeEngine(), tts=_FakeTTS())
    assert res["text"] == "真人这么讲"
    assert (tmp_path / "c1" / "human" / "audio.wav").read_bytes() == b"RIFFfake"


def test_machine_variants_share_retrieval_seed_and_exclude_source(tmp_path: Path):
    fixture = {
        "id": "c1__r02",
        "source_fixture_id": "c1",
        "repeat": 2,
        "split": "dev",
        "topic": "t",
        "_retrieval_allowed_ids": ["train1", "train2"],
        "_tuning_guidance": [{
            "id": "note-1",
            "category": "repetition",
            "rule": "同一数字只出现一次",
        }],
        "tone_intent": "playful_teasing",
        "depth_budget": "light",
        "entertainment_mechanism": "故作认真后反转",
    }
    with_engine = _FakeEngine()
    without_engine = _FakeEngine()
    generate_variant(
        fixture, "with_dossier", str(tmp_path),
        engine_factory=lambda: with_engine, tts=_FakeTTS(),
    )
    generate_variant(
        fixture, "no_dossier", str(tmp_path),
        engine_factory=lambda: without_engine, tts=_FakeTTS(),
    )
    expected_seed = stable_retrieval_seed(fixture)
    for engine in (with_engine, without_engine):
        assert engine.setup_kwargs["retrieval_seed"] == expected_seed
        assert engine.setup_kwargs["retrieval_allowed_ids"] == ["train1", "train2"]
        assert engine.setup_kwargs["retrieval_exclude_ids"] == ["c1"]
        assert engine.setup_kwargs["tuning_guidance"][0]["id"] == "note-1"
        assert engine.setup_kwargs["tone_intent"] == "playful_teasing"
        assert engine.setup_kwargs["depth_budget"] == "light"
        assert engine.setup_kwargs["entertainment_mechanism"] == "故作认真后反转"
