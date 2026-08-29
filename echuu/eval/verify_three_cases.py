"""Generate the 3 listening fixtures on the live default pipeline (legacy_v4)
and print leak / completeness / runaway checks. Text only, no TTS.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from echuu.core.prompt_leakage import find_prompt_leaks
from echuu.eval.generate import generate_variant
from echuu.live.engine import EchuuLiveEngine

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
BASELINE_DIR = EVAL_DIR / "runs" / "verify-2026-08-30"
OUT_DIR = EVAL_DIR / "runs" / "verify-2026-08-30-v2"
FIXTURES = EVAL_DIR / "legacy_v4_cases.jsonl"

# Extra audience-facing slips V4 historically produces (not in INTERNAL_PROMPT_MARKERS).
STOCK_ASIDES = (
    "严重跑题一下",
    "下一个话题",
    "内心戏？",
    "失控？",
)

META_SLIPS = (
    "这句删掉",
    "只输出 JSON",
    "只输出JSON",
    "SYSTEM",
    "你是一个模拟",
    "核心认知",
    "故事内核",
    "key_info",
    "interruption_cost",
    "trigger_type",
    "ScriptLine",
    "JSON 数组",
    "不要其他内容",
)

TOPIC_ANCHORS = {
    "moving_rice_cooker": ("电饭锅", "搬家", "保温"),
    "wrong_takeout": ("外卖", "送错"),
    "rainy_day_umbrella": ("伞", "雨"),
}


def load_fixtures() -> list[dict]:
    return [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]


def score_case(fixture: dict, text: str, trace: dict) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    leaks = list(find_prompt_leaks(text))
    slips = [m for m in META_SLIPS if m in text]
    anchors = TOPIC_ANCHORS[fixture["id"]]
    hit = [a for a in anchors if a in text]
    missing = [a for a in anchors if a not in text]
    topic_literal = fixture["topic"]
    topic_dumped = topic_literal in text
    stock = [m for m in STOCK_ASIDES if m in text]
    # Crude runaway: a line that mentions none of the anchors and is long.
    stray = []
    for ln in lines:
        if len(ln) >= 40 and not any(a in ln for a in anchors):
            stray.append(ln[:80])
    pipeline = trace.get("pipeline") or (trace.get("evaluation_context") or {}).get("story_pipeline")
    return {
        "id": fixture["id"],
        "topic": fixture["topic"],
        "pipeline": pipeline,
        "line_count": len(lines),
        "chars": len(text),
        "prompt_leaks": leaks,
        "meta_slips": slips,
        "anchors_hit": hit,
        "anchors_missing": missing,
        "topic_string_dumped": topic_dumped,
        "stock_asides": stock,
        "stray_long_lines": stray[:6],
        "ok_complete": len(lines) >= 6 and not missing,
        "ok_leak": not leaks and not slips,
        "ok_on_topic": len(hit) == len(anchors),
        "ok_no_topic_dump": not topic_dumped,
        "ok_no_stock": not stock,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = load_fixtures()
    reports = []
    for fx in fixtures:
        run_fx = {**fx, "source_fixture_id": fx["id"], "repeat": 1, "id": fx["id"]}
        print(f"\n======== generate {fx['id']} / legacy_v4 ========", flush=True)
        result = generate_variant(
            run_fx,
            "legacy_v4",
            str(OUT_DIR),
            engine_factory=EchuuLiveEngine,
            tts=None,
            metadata={"purpose": "verify-2026-08-30-v2", "text_only": True},
        )
        text = result["text"]
        trace = json.loads((OUT_DIR / fx["id"] / "legacy_v4" / "trace.json").read_text(encoding="utf-8"))
        report = score_case(fx, text, trace)
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        print("--- script ---", flush=True)
        print(text, flush=True)

    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsummary → {summary_path}", flush=True)
    baseline_path = BASELINE_DIR / "summary.json"
    if baseline_path.exists():
        baseline = {row["id"]: row for row in json.loads(baseline_path.read_text(encoding="utf-8"))}
        print("\n======== vs verify-2026-08-30 ========", flush=True)
        for row in reports:
            old = baseline.get(row["id"], {})
            print(
                f"{row['id']}: dump {old.get('topic_string_dumped')}→{row['topic_string_dumped']} "
                f"stock {old.get('stock_asides', [])}→{row['stock_asides']} "
                f"lines {old.get('line_count')}→{row['line_count']}",
                flush=True,
            )
    failed = [
        r for r in reports
        if not (r["ok_complete"] and r["ok_leak"] and r["ok_on_topic"] and r["ok_no_topic_dump"] and r["ok_no_stock"])
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
