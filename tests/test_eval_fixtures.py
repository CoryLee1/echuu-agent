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


def test_build_fixtures_skips_empty_title_and_bounds_n(tmp_path: Path):
    """Regression: empty-title clip among first records is skipped, n still yields valid fixtures from later clips."""
    clips = tmp_path / "clips.jsonl"
    rows = [
        {"clip_id": "a", "title": "", "transcript": [{"t": 0, "text": "skip me"}]},
        {"clip_id": "b", "title": "有题目B", "transcript": [{"t": 0, "text": "bbb"}]},
        {"clip_id": "c", "title": "有题目C", "transcript": [{"t": 0, "text": "ccc"}]},
    ]
    clips.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    out = tmp_path / "fixtures.jsonl"
    n = build_fixtures(str(clips), str(out), n=1)  # empty-title first, n=1 must still yield 1 valid
    assert n == 1
    got = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert got["topic"] == "有题目B"  # skipped the empty-title clip, took the next valid one
