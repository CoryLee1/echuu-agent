"""从真实 clip jsonl 抽评测题目：topic(title) + 真人 transcript 拼接。"""
from __future__ import annotations

import json
import re
from pathlib import Path


_CURATED_CREATIVE_DIRECTIONS = {
    # 2026-07-26 human review: the previous title/background over-weighted the
    # mock-serious setup and made the model invent power/contract theories.
    "clip_012": {
        "topic": "Daddy称呼的轻松调笑",
        "persona_feature": "擅长故作认真地吊观众胃口，再用暧昧玩笑和截断式反转收尾",
        "background": "表面认真解释称呼含义与使用边界，实际持续调笑、吊胃口，最后在答案处截断抖包袱",
        "tone_intent": "playful_teasing",
        "depth_budget": "light",
        "entertainment_mechanism": "故作认真 + 暧昧吊胃口 + 结尾截断反转",
    },
}

# Once a human correction is used to change a fixture or its prompts, that
# creator group is no longer an untouched TEST group. Keep the fold sizes at
# 20/5/5 by swapping two previously untouched singleton DEV fixtures.
_POST_REVIEW_SPLIT_OVERRIDES = {
    "clip_012": "dev",
    "clip_020": "dev",
    "clip_006": "test",
    "clip_019": "test",
}


def _load(clips_path: str) -> list[dict]:
    out = []
    for line in Path(clips_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _source_group(clip: dict) -> str:
    """Group named creators together; generic source labels stay clip-specific."""
    source = str(clip.get("source", ""))
    match = re.search(r"\(([^)]+)\)", source)
    if match:
        named = match.group(1).strip()
        generic_markers = ("杂谈", "访谈", "联动", "学术", "宠物", "回忆", "职业")
        if named and not any(marker in named for marker in generic_markers):
            return named.casefold()
    return str(clip.get("clip_id") or clip.get("title") or "unknown")


def _assign_grouped_splits(rows: list[dict]) -> None:
    """In-place deterministic 4:1:1 split without putting one creator in two folds."""
    total = len(rows)
    targets = {
        "train": round(total * 2 / 3),
        "dev": round(total / 6),
    }
    targets["test"] = total - targets["train"] - targets["dev"]
    counts = {name: 0 for name in targets}
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["source_group"], []).append(row)

    order = {"train": 0, "dev": 1, "test": 2}
    for _, grouped_rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        size = len(grouped_rows)
        eligible = [
            split for split, target in targets.items()
            if counts[split] + size <= target
        ] or list(targets)
        split = min(
            eligible,
            key=lambda name: (
                counts[name] / max(targets[name], 1),
                order[name],
            ),
        )
        counts[split] += size
        for row in grouped_rows:
            row["split"] = split
    if set(_POST_REVIEW_SPLIT_OVERRIDES).issubset({row["id"] for row in rows}):
        for row in rows:
            override = _POST_REVIEW_SPLIT_OVERRIDES.get(row["id"])
            if override:
                row["split"] = override


def build_fixtures(clips_path: str, out_path: str, n: int | None = None) -> int:
    clips = _load(clips_path)
    rows = []
    for c in clips:
        title = str(c.get("title", "")).strip()
        if not title:
            continue
        segs = c.get("transcript", []) or []
        human = "\n".join(str(s.get("text", "")).strip() for s in segs if s.get("text"))
        notes = c.get("notes") if isinstance(c.get("notes"), dict) else {}
        direction = _CURATED_CREATIVE_DIRECTIONS.get(str(c.get("clip_id", "")), {})
        persona_parts = [
            str(c.get("source", "")).strip(),
            str(direction.get("persona_feature", notes.get("feature", ""))).strip(),
            f"常用表达：{notes.get('habit')}" if notes.get("habit") else "",
        ]
        rows.append({
            "id": c.get("clip_id", title),
            "source_group": _source_group(c),
            "topic": direction.get("topic", title),
            "persona": "；".join(p for p in persona_parts if p),
            "background": str(direction.get("background", notes.get("emotion", ""))).strip(),
            "tone_intent": direction.get("tone_intent", notes.get("tone_intent", "auto")),
            "depth_budget": direction.get("depth_budget", notes.get("depth_budget", "auto")),
            "entertainment_mechanism": direction.get(
                "entertainment_mechanism",
                notes.get("entertainment_mechanism", ""),
            ),
            "human_transcript": human,
        })
        if n is not None and len(rows) >= n:
            break
    _assign_grouped_splits(rows)
    Path(out_path).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    src = root / "data" / "vtuber_raw_clips_for_notebook_full_30_cleaned.jsonl"
    dst = Path(__file__).resolve().parent / "fixtures.jsonl"
    print(f"wrote {build_fixtures(str(src), str(dst))} fixtures → {dst}")
