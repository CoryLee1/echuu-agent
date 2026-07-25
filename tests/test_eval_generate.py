from pathlib import Path
from echuu.eval.generate import render_script, generate_variant


class _FakeEngine:
    """run() 产出两条 step 事件，setup 记录 enable_dossier。"""
    def __init__(self): self.enable = None
    def setup(self, **kw): self.enable = kw.get("enable_dossier"); return self
    def run(self, **kw):
        yield {"speech": "第一句"}
        yield {"speech": "第二句"}


class _FakeTTS:
    def synthesize(self, text): return b"RIFFfake"


def test_render_script_joins_speech():
    txt = render_script(_FakeEngine())
    assert txt == "第一句\n第二句"


def test_generate_variant_writes_text_and_audio(tmp_path: Path):
    fx = {"id": "c1", "topic": "帮朋友做决定", "human_transcript": "真人这么讲"}
    eng = _FakeEngine()
    res = generate_variant(fx, "with_dossier", str(tmp_path),
                           engine_factory=lambda: eng, tts=_FakeTTS())
    assert eng.enable is True
    assert res["variant"] == "with_dossier"
    assert (tmp_path / "c1" / "with_dossier" / "text.txt").read_text(encoding="utf-8") == "第一句\n第二句"
    assert (tmp_path / "c1" / "with_dossier" / "audio.wav").read_bytes() == b"RIFFfake"


def test_generate_human_variant_uses_transcript(tmp_path: Path):
    fx = {"id": "c1", "topic": "t", "human_transcript": "真人这么讲"}
    res = generate_variant(fx, "human", str(tmp_path),
                           engine_factory=lambda: _FakeEngine(), tts=_FakeTTS())
    assert res["text"] == "真人这么讲"
    assert (tmp_path / "c1" / "human" / "audio.wav").read_bytes() == b"RIFFfake"
