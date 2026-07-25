"""pairwise 评测 CLI：generate（生成三方变体）+ report（读 judgments 出胜率）。

report 把 (with_dossier vs no_dossier) 作为核心消融：胜率落 40-60% → 扩充无效。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
RUNS_DIR = EVAL_DIR / "runs"
JUDGMENTS = EVAL_DIR / "judgments.jsonl"
FIXTURES = EVAL_DIR / "fixtures.jsonl"

VARIANTS = ("human", "with_dossier", "no_dossier")


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def win_rate(judgments: list[dict], a: str, b: str) -> dict:
    """a vs b 的胜率（winner 是 'a'/'b'/'tie'，相对每条的 variant_a/variant_b）。"""
    n = wins_a = 0
    for j in judgments:
        va, vb, w = j.get("variant_a"), j.get("variant_b"), j.get("winner")
        pair = {va, vb}
        if pair != {a, b} or w == "tie":
            continue
        n += 1
        winner_variant = va if w == "a" else vb
        if winner_variant == a:
            wins_a += 1
    rate = (wins_a / n) if n else 0.0
    low, high = wilson_interval(wins_a, n)
    return {"n": n, "wins_a": wins_a, "rate": rate, "low": low, "high": high}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_generate() -> None:
    from echuu.live.engine import EchuuLiveEngine
    from echuu.live.tts_client import TTSClient
    from echuu.eval.generate import generate_variant

    fixtures = _load_jsonl(FIXTURES)
    tts = TTSClient()
    for fx in fixtures:
        for variant in VARIANTS:
            print(f"[gen] {fx['id']} / {variant}")
            generate_variant(fx, variant, str(RUNS_DIR),
                             engine_factory=EchuuLiveEngine, tts=tts)
    print(f"done → {RUNS_DIR}")


def cmd_report() -> None:
    judgments = _load_jsonl(JUDGMENTS)
    pairs = [("with_dossier", "no_dossier"), ("with_dossier", "human"),
             ("no_dossier", "human")]
    print(f"judgments: {len(judgments)}")
    for a, b in pairs:
        r = win_rate(judgments, a, b)
        verdict = ""
        if a == "with_dossier" and b == "no_dossier" and r["n"]:
            verdict = "  ← 40-60% 判扩充无效" if 0.4 <= r["rate"] <= 0.6 else ""
        print(f"{a:>13} vs {b:<12} n={r['n']:>3} 胜率={r['rate']:.0%} "
              f"[{r['low']:.0%},{r['high']:.0%}]{verdict}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"generate": cmd_generate, "report": cmd_report}.get(cmd, cmd_report)()
