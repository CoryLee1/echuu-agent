"""Qwen diary cover: screenshot + diary text in one multimodal call.

DashScope result URLs expire in 24h, so we download immediately.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from ..config import DIARY_COVERS_DIR
except ImportError:
    from config import DIARY_COVERS_DIR

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DASHSCOPE_API_ROOT = (os.getenv("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
DASHSCOPE_EDIT_URL = f"{DASHSCOPE_API_ROOT}/services/aigc/multimodal-generation/generation"
QWEN_EDIT_MODELS = (
    os.getenv("DIARY_COVER_MODEL") or "qwen-image-edit-max",
    "qwen-image-edit-plus",
    "qwen-image-edit",
)
# Official 3:4 sizes for qwen-image-edit-plus
COVER_SIZE = "1080*1440"
DEFAULT_CHARACTER_REF = (
    Path(__file__).resolve().parents[1] / "assets" / "diary-character-refs" / "cathy.jpg"
)

NEGATIVE_PROMPT = (
    "different face, different hair, different outfit, another character, "
    "3D render, VRM, live2D plastic, game screenshot, Unreal Engine, "
    "photoreal, cinematic film still, realistic skin, subsurface scattering, "
    "sketchbook, notebook, spiral binding, manga page, rough lineart, "
    "open notebook, diary book, pink milk, strawberry milk, "
    "beer bottle, wine bottle, liquor bottle, brown long-neck bottle, alcohol, "
    "diary page, handwritten notes, scrapbook, still life only, "
    "UI, calendar, buttons, icons, watermark, subtitle, caption, letters, text, Chinese characters, "
    "English words, logo, title card, "
    "white studio background, empty backdrop, plain white void, outdoor blue sky portrait, "
    "standing character sheet, waist-up idol pose, looking at camera with empty hands, "
    "smiling portrait, character sheet, tiny unreadable props, "
    "snake, animal straw, extra people"
)

def cover_public_path(session_id: str, ext: str = "jpg") -> str:
    path = cover_file_path(session_id, ext)
    url = f"/diary-covers/{session_id}.{ext}"
    if path.is_file():
        url = f"{url}?v={int(path.stat().st_mtime)}"
    return url


def cover_file_path(session_id: str, ext: str = "jpg") -> Path:
    DIARY_COVERS_DIR.mkdir(parents=True, exist_ok=True)
    return DIARY_COVERS_DIR / f"{session_id}.{ext}"


def existing_cover_url(session_id: str) -> str | None:
    if not session_id:
        return None
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = cover_file_path(session_id, ext)
        if path.is_file() and path.stat().st_size > 1024:
            return cover_public_path(session_id, ext)
    return None


def character_ref_path(diary: dict[str, Any] | None = None) -> Path:
    override = str((diary or {}).get("cover_ref_path") or os.getenv("DIARY_COVER_REF_IMAGE") or "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return path
    return DEFAULT_CHARACTER_REF


def style_ref_path(diary: dict[str, Any] | None = None) -> Path | None:
    override = str((diary or {}).get("cover_style_ref_path") or os.getenv("DIARY_COVER_STYLE_REF") or "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    return None


_YOGURT_BOTTLE = (
    "a short clear drinkable-yogurt bottle (Yakult / yogurt-drink shape: "
    "wide body, short neck, white yogurt inside) — NOT a brown beer, wine, or liquor bottle"
)


def cover_visual_beat(diary: dict[str, Any]) -> str:
    text = "".join(
        str(diary.get(key) or "")
        for key in ("title", "lede", "scene", "voice_note")
    )
    if any(token in text for token in ("酸奶", "吸管", "太阳")):
        return (
            f"Show {_YOGURT_BOTTLE} on a desk, being pushed away or left unfinished, "
            "with a sun sticky note on the bottle and a bent plastic straw."
        )
    if any(token in text for token in ("饭盒", "筷子", "胃口", "没胃口", "饭团")):
        return (
            "FOREGROUND MUST BE an opened lunch box with leftover rice and chopsticks on the lid — "
            "large enough to read, steam still rising. She sits at the desk looking DOWN at the leftover food, "
            "one bite taken, no appetite, empty expression, pretending she is fine. "
            "Hands are on the chopsticks or the box, not empty. She is not looking at the camera. "
            "Indoor wooden desk, chair, warm window light. Not standing outdoors. Not a sky backdrop."
        )
    if any(token in text for token in ("八卦", "上司", "咽回去", "有瓜")):
        return (
            "FOREGROUND MUST BE her fingers covering her mouth as she swallows gossip. "
            "Lean in as if to spill it, then clamp the words back. Eyes darting, not a cute idle pose. "
            "A black desk microphone sits nearby with no letters on it. After-hours indoor desk. "
            "Hands are on her mouth, not empty in her lap. She is not looking at the camera. "
            "Warm indoor light and room depth. No second person. Not a white studio background."
        )
    return "Show one concrete object and action from the diary text, large enough to read as the story."


def build_diary_cover_prompt(diary: dict[str, Any]) -> str:
    title = str(diary.get("title") or "").strip()
    lede = str(diary.get("lede") or "").strip()
    scene = str(diary.get("scene") or "").strip()
    if diary.get("cover_remove_text"):
        return (
            "Keep the exact composition, pose, camera, lighting, room, and character. "
            "Do not redraw the scene.\n"
            "ONLY erase every letter, word, logo, caption, watermark, and printed graphic text. "
            "Clothes must have no words. Background must have no words. "
            "Replace text on shirts with a plain color block or abstract pattern. "
            "No new text of any kind."
        )
    if diary.get("cover_fix"):
        return (
            "Keep the exact composition, camera, lighting, room, desk, and character. "
            "Do not redraw the scene.\n"
            f"ONLY change this acting beat: {diary['cover_fix']}\n"
            "No text, no letters, no watermark, no words on clothes."
        )
    if diary.get("cover_refine"):
        return (
            "This illustration is almost correct. Keep the exact composition, pose, camera, lighting, "
            "room, chair, desk, and character. Do not redraw the scene.\n"
            f"ONLY replace the brown liquor/beer bottle with {_YOGURT_BOTTLE}. "
            "Add a tiny sun sticky note on the yogurt bottle and a bent plastic drinking straw "
            "in the mouth (plastic straw only, not a snake).\n"
            "No text, no letters, no watermark, no words on clothes."
        )
    style_note = ""
    if diary.get("cover_use_style_ref") or style_ref_path(diary):
        style_note = (
            "Image 1 is the character screenshot (face and outfit). "
            "Image 2 is a QUALITY TARGET only: copy its 2D polish, warm indoor window light, "
            "seated desk story, chair, and background depth. "
            "Do NOT copy Image 2's yogurt bottle, straw, sun sticker, or pose.\n"
        )
    return (
        f"{style_note}"
        "THIS IMAGE FAILS if the story object is missing or if she is a smiling empty-handed portrait.\n"
        f"Required visual beat (must dominate the frame): {cover_visual_beat(diary)}\n"
        "Keep the exact girl from this screenshot as the only subject. "
        "Same face, same navy twin-tails, same white-and-black jacket, same pink skirt, same choker. "
        "Do not replace her with another anime character. Do not write any name on the image.\n"
        "CRITICAL style: turn this into a polished 2D anime illustration / Xiaohongshu cover art. "
        "Clean linework, flat-to-soft cel coloring, illustration lighting — "
        "not a 3D VRM capture, not a game screenshot, not photoreal CGI, not a sketchbook page.\n"
        "Quality bar: seated indoor story, warm directional window light, soft room depth "
        "(desk, chair, bookshelf or office). Finished illustration, not a character sheet.\n"
        "Forbidden compositions: white studio void, empty blue sky, standing waist-up portrait, "
        "camera-facing empty hands, tiny props that cannot be read as the story.\n"
        "Output a vertical 3:4 illustration that tells THIS diary only. "
        "Change the composition and pose a lot: new camera angle, new body language, not a standing front portrait. "
        "Do not copy the screenshot pose.\n"
        "Do not invent yogurt, Yakult, a drink bottle, or a straw unless the diary mentions yogurt. "
        "ABSOLUTELY NO TEXT anywhere: no letters, no numbers, no logos, no captions, no watermarks, "
        "no words on clothes, no title cards. The shirt graphic must be abstract shapes only.\n"
        "Remove all UI, calendar, buttons, icons, subtitles, watermarks, and notebook frames.\n"
        "Story to illustrate (do not paint these sentences onto the picture):\n"
        f"Title: {title}\n"
        f"Body: {lede}\n"
        f"Scene: {scene}"
    )


def ensure_diary_cover(diary: dict[str, Any], *, force: bool = False) -> str | None:
    current = str(diary.get("cover_url") or "").strip()
    if current and not force:
        return current
    session_id = str(diary.get("session_id") or "").strip()
    if not force:
        existing = existing_cover_url(session_id)
        if existing:
            return existing
    if os.getenv("DIARY_COVER_GENERATE", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    return generate_diary_cover(diary)


def generate_diary_cover(diary: dict[str, Any]) -> str | None:
    session_id = str(diary.get("session_id") or "").strip()
    if not session_id:
        return None
    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        print("[diary] cover skipped: DASHSCOPE_API_KEY missing")
        return None
    ref = character_ref_path(diary)
    if not ref.is_file():
        print(f"[diary] cover skipped: character screenshot missing ({ref})")
        return None

    prompt = build_diary_cover_prompt(diary)
    refs = [ref]
    style = style_ref_path(diary)
    if style and style.resolve() != ref.resolve():
        refs.append(style)
    image_url = _edit_with_screenshot(api_key, refs, prompt)
    if not image_url:
        return None
    ext, blob = _download_image(image_url)
    path = cover_file_path(session_id, ext)
    path.write_bytes(blob)
    return cover_public_path(session_id, ext)


def _edit_with_screenshot(api_key: str, image_paths: Path | list[Path], prompt: str) -> str:
    paths = image_paths if isinstance(image_paths, list) else [image_paths]
    content = [{"image": _image_data_url(path)} for path in paths if path and path.is_file()]
    content.append({"text": prompt})
    payload = {
        "model": "",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ]
        },
        "parameters": {
            "n": 1,
            "size": COVER_SIZE,
            "watermark": False,
            "prompt_extend": False,
            "negative_prompt": NEGATIVE_PROMPT,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error = "qwen image edit failed"
    seen: set[str] = set()
    for model in QWEN_EDIT_MODELS:
        if not model or model in seen:
            continue
        seen.add(model)
        payload["model"] = model
        try:
            data = _request_json("POST", DASHSCOPE_EDIT_URL, headers, payload, timeout=120)
        except RuntimeError as exc:
            last_error = str(exc)
            if _should_try_next_model(last_error):
                continue
            raise
        url = _image_url_from_edit(data)
        if url:
            return url
        last_error = str(data.get("message") or data.get("code") or "no image url")
        if _should_try_next_model(last_error):
            continue
        raise RuntimeError(last_error)
    raise RuntimeError(last_error)


def _should_try_next_model(message: str) -> bool:
    text = message.lower()
    return any(token in text for token in ("model", "not found", "invalidparameter", "accessdenied", "403", "404"))


def _image_url_from_edit(data: dict[str, Any]) -> str | None:
    output = data.get("output") or {}
    for choice in output.get("choices") or []:
        message = (choice or {}).get("message") or {}
        for item in message.get("content") or []:
            if isinstance(item, dict):
                url = str(item.get("image") or "")
                if url:
                    return url
    results = output.get("results") or []
    if results and isinstance(results[0], dict):
        url = str(results[0].get("url") or results[0].get("image") or "")
        if url:
            return url
    return None


def _image_data_url(path: Path) -> str:
    blob = path.read_bytes()
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(blob).decode('ascii')}"


def _download_image(url: str) -> tuple[str, bytes]:
    last_error: Exception | None = None
    blob = b""
    content_type = ""
    for _attempt in range(3):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=45) as resp:
                blob = resp.read()
                content_type = str(resp.headers.get("Content-Type") or "")
            if len(blob) >= 1024:
                break
            last_error = RuntimeError("qwen image download too small")
        except Exception as exc:  # noqa: BLE001 — 结果链 24h 内偶发截断
            last_error = exc
    else:
        raise last_error or RuntimeError("qwen image download failed")
    if "png" in content_type or blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", blob
    if "webp" in content_type or blob[:4] == b"RIFF":
        return "webp", blob
    return "jpg", blob


def _request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"dashscope {exc.code}: {detail}") from exc
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}
