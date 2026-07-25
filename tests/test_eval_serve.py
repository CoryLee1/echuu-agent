import json
from pathlib import Path
from fastapi.testclient import TestClient


def _seed_runs(root: Path):
    for variant in ("human", "with_dossier", "no_dossier"):
        d = root / "runs" / "c1" / variant
        d.mkdir(parents=True, exist_ok=True)
        (d / "text.txt").write_text(f"{variant} 文本", encoding="utf-8")
        (d / "audio.wav").write_bytes(b"RIFFxx")


def _app(tmp_path):
    _seed_runs(tmp_path)
    from echuu.eval import serve
    serve.RUNS_DIR = tmp_path / "runs"
    serve.JUDGMENTS = tmp_path / "judgments.jsonl"
    return serve.app


def test_next_returns_anonymized_pair(tmp_path):
    client = TestClient(_app(tmp_path))
    r = client.get("/api/next").json()
    assert r["fixture_id"] == "c1"
    assert {r["a"]["variant"], r["b"]["variant"]} <= {"human", "with_dossier", "no_dossier"}
    assert r["a"]["variant"] != r["b"]["variant"]
    assert r["a"]["text"]  # 文本已带出


def test_judge_appends_jsonl(tmp_path):
    client = TestClient(_app(tmp_path))
    from echuu.eval import serve
    payload = {"fixture_id": "c1", "variant_a": "with_dossier",
               "variant_b": "no_dossier", "winner": "a"}
    assert client.post("/api/judge", json=payload).status_code == 200
    rows = [json.loads(l) for l in serve.JUDGMENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows[-1]["winner"] == "a" and rows[-1]["fixture_id"] == "c1"


def test_audio_missing_returns_404(tmp_path):
    app = _app(tmp_path)
    # text.txt exists (from _seed_runs) but audio.wav is missing for this variant
    # (TTS failed/skipped case) — /audio must 404, not 500.
    (tmp_path / "runs" / "c1" / "with_dossier" / "audio.wav").unlink()
    client = TestClient(app)
    assert client.get("/audio/c1/with_dossier").status_code == 404
    assert client.get("/audio/c1/bogus_variant").status_code == 404
