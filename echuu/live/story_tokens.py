"""Story tokens for the tangent hunt — entities, not word pieces."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

TOKEN_KINDS = ("item", "time", "person", "event")
STOPWORDS = {
    "的", "了", "呢", "吧", "啊", "然后", "就是", "这个", "那个",
    "我们", "你们", "一下", "什么", "怎么", "因为", "所以",
}
TIME_MARKERS = ("那天", "那天晚上", "夜里", "半夜", "那年", "去年", "春天", "梅雨", "昨天", "早上")
PERSON_MARKERS = ("姐姐", "阿姨", "前任", "朋友", "小孩", "同学", "妈妈", "我妈", "林先生", "王女士")


def classify_kind(label: str) -> str:
    text = (label or "").strip()
    if any(marker in text for marker in TIME_MARKERS) or text.endswith("年"):
        return "time"
    if any(marker in text for marker in PERSON_MARKERS):
        return "person"
    if len(text) <= 4 and not text.endswith("了"):
        return "item"
    return "event"


def extract_tokens_from_line(
    text: str,
    key_info: Iterable[str] | None,
    line_id: str,
    *,
    limit: int = 3,
) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in key_info or []:
        label = str(raw or "").strip()
        if not label or label in STOPWORDS or label in seen:
            continue
        if text and label not in text and not any(part in text for part in re.split(r"[的了]", label) if len(part) >= 2):
            # still allow key_info that names the entity even if the spoken chunk split it
            pass
        kind = classify_kind(label)
        token_id = f"t_{label}_{line_id}"
        tokens.append({"id": token_id, "label": label, "kind": kind, "sourceLineId": line_id})
        seen.add(label)
        if len(tokens) >= limit:
            return tokens
    return tokens


def compose_tangent_text(entities: list[dict[str, Any]] | list[Any]) -> str:
    labels = []
    for item in entities:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
        else:
            label = str(getattr(item, "label", "") or "").strip()
        if label:
            labels.append(label)
    joined = " × ".join(labels) if labels else "刚才那几件事"
    return f"沿着「{joined}」往下讲一小段，1到2句后必须说回主线，不准另开新故事"


@dataclass
class TokenHunt:
    """Shared collect-3 tray. Audience fills it; host fires the pending card."""

    slots: list[dict[str, str]] = field(default_factory=list)
    pending: list[dict[str, str]] | None = None

    def collect(self, token: dict[str, Any] | None) -> dict[str, Any]:
        if not token or not token.get("id") or not token.get("label"):
            return {"slots": list(self.slots), "pending": self.pending, "crafted": None}
        token_id = str(token["id"])
        if any(item.get("id") == token_id for item in self.slots):
            return {"slots": list(self.slots), "pending": self.pending, "crafted": None}
        if self.pending and any(item.get("id") == token_id for item in self.pending):
            return {"slots": list(self.slots), "pending": self.pending, "crafted": None}
        cleaned = {
            "id": token_id,
            "label": str(token.get("label") or "").strip(),
            "kind": str(token.get("kind") or "event"),
            "sourceLineId": str(token.get("sourceLineId") or ""),
        }
        self.slots = [*self.slots, cleaned]
        return {"slots": list(self.slots), "pending": self.pending, "crafted": None}

    def maybe_craft(self, ready: bool) -> dict[str, Any]:
        crafted = None
        if ready and self.pending is None and len(self.slots) >= 3:
            crafted = list(self.slots[:3])
            self.pending = crafted
            self.slots = self.slots[3:]
        return {"slots": list(self.slots), "pending": self.pending, "crafted": crafted}

    def consume_pending(self) -> list[dict[str, str]] | None:
        card = self.pending
        self.pending = None
        return card

    def snapshot(self) -> dict[str, Any]:
        return {"slots": list(self.slots), "pending": self.pending}
