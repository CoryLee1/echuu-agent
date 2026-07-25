"""独立评测后台：盲测二选一 + 文本双栏 + TTS 试听。随起随用，不接 echuu-web。

跑：uvicorn echuu.eval.serve:app --port 8900   然后开 http://localhost:8900
"""
from __future__ import annotations

import json
import random
from itertools import combinations
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

EVAL_DIR = Path(__file__).resolve().parent
RUNS_DIR = EVAL_DIR / "runs"
JUDGMENTS = EVAL_DIR / "judgments.jsonl"
STATIC = EVAL_DIR / "static"
VARIANTS = ("human", "with_dossier", "no_dossier")

app = FastAPI(title="echuu eval")


class Judge(BaseModel):
    fixture_id: str
    variant_a: str
    variant_b: str
    winner: str  # "a" | "b" | "tie"


def _read_text(fixture_id: str, variant: str) -> str:
    f = RUNS_DIR / fixture_id / variant / "text.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def _judged_pairs() -> set:
    seen = set()
    if JUDGMENTS.exists():
        for line in JUDGMENTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                j = json.loads(line)
                seen.add((j["fixture_id"], frozenset((j["variant_a"], j["variant_b"]))))
    return seen


def _all_pairs() -> list[tuple[str, str, str]]:
    """所有 (fixture_id, va, vb)，仅当两变体产物都存在。"""
    out = []
    if not RUNS_DIR.exists():
        return out
    for fx_dir in sorted(RUNS_DIR.iterdir()):
        if not fx_dir.is_dir():
            continue
        present = [v for v in VARIANTS if (fx_dir / v / "text.txt").exists()]
        for a, b in combinations(present, 2):
            out.append((fx_dir.name, a, b))
    return out


@app.get("/api/next")
def next_pair():
    judged = _judged_pairs()
    pairs = _all_pairs()
    pending = [p for p in pairs if (p[0], frozenset((p[1], p[2]))) not in judged]
    pool = pending or pairs
    if not pool:
        return {"done": True}
    fx, va, vb = random.choice(pool)
    # 随机左右，来源匿名（前端只显示 A/B）
    left, right = random.sample([va, vb], 2)
    return {
        "done": False,
        "fixture_id": fx,
        "a": {"variant": left, "text": _read_text(fx, left),
              "audio_url": f"/audio/{fx}/{left}"},
        "b": {"variant": right, "text": _read_text(fx, right),
              "audio_url": f"/audio/{fx}/{right}"},
    }


@app.post("/api/judge")
def judge(j: Judge):
    with JUDGMENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(j.model_dump(), ensure_ascii=False) + "\n")
    return {"ok": True}


@app.get("/audio/{fixture_id}/{variant}")
def audio(fixture_id: str, variant: str):
    return FileResponse(RUNS_DIR / fixture_id / variant / "audio.wav",
                        media_type="audio/wav")


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "review.html").read_text(encoding="utf-8")
