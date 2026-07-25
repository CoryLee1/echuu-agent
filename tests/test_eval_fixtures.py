import json
from pathlib import Path
from echuu.eval.build_fixtures import build_fixtures


def test_build_fixtures_from_clips(tmp_path: Path):
    clips = tmp_path / "clips.jsonl"
    rows = [
        {"clip_id": "c1", "title": "帮朋友做决定这件事",
         "transcript": [{"t": 0, "text": "你们有没有过"}, {"t": 5, "text": "帮人选完他还怪你"}]},
        {"clip_id": "c2", "title": "云养猫",
         "transcript": [{"t": 0, "text": "我最近沉迷看别人的猫"}]},
    ]
    clips.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    out = tmp_path / "fixtures.jsonl"
    n = build_fixtures(str(clips), str(out), n=8)
    assert n == 2
    got = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert got[0]["topic"] == "帮朋友做决定这件事"
    assert "帮人选完他还怪你" in got[0]["human_transcript"]
    assert got[0]["id"] == "c1"
