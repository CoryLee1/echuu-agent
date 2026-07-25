"""从真实 clip jsonl 抽评测题目：topic(title) + 真人 transcript 拼接。"""
from __future__ import annotations

import json
from pathlib import Path


def _load(clips_path: str) -> list[dict]:
    out = []
    for line in Path(clips_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def build_fixtures(clips_path: str, out_path: str, n: int = 8) -> int:
    clips = _load(clips_path)
    rows = []
    for c in clips[:n]:
        title = str(c.get("title", "")).strip()
        if not title:
            continue
        segs = c.get("transcript", []) or []
        human = "\n".join(str(s.get("text", "")).strip() for s in segs if s.get("text"))
        rows.append({"id": c.get("clip_id", title), "topic": title,
                     "human_transcript": human})
    Path(out_path).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    src = root / "data" / "vtuber_raw_clips_for_notebook_full_30_cleaned.jsonl"
    dst = Path(__file__).resolve().parent / "fixtures.jsonl"
    print(f"wrote {build_fixtures(str(src), str(dst), n=8)} fixtures → {dst}")
