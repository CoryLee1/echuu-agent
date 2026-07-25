"""三方变体生成：真人 transcript / 有扩充 / 无扩充，各产出 text + 一段 TTS wav。

机器变体驱动完整引擎（setup + run），拿 step 事件文本拼成整份剧本再整段合成音频，
保证评测台三栏都能试听、盲测不被"有没有音频"泄底。
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable


def render_script(engine) -> str:
    """驱动 engine.run()，把每个 step 的 speech 拼成整份剧本文本。"""
    lines = []
    for ev in engine.run(max_steps=15, play_audio=False, save_audio=False):
        sp = (ev.get("speech") or ev.get("line", {}).get("text") or "").strip()
        if sp:
            lines.append(sp)
    return "\n".join(lines)


def synth_audio(tts, text: str, out_wav: Path) -> None:
    audio = tts.synthesize(text) if text else b""
    out_wav.write_bytes(audio or b"")


def _machine_text(fixture: dict, enable_dossier: bool, engine_factory: Callable) -> str:
    engine = engine_factory()
    engine.setup(
        name=fixture.get("character_name", "评测主播"),
        persona=fixture.get("persona", "普通、爱观察生活的直播主播"),
        background=fixture.get("background", ""),
        topic=fixture["topic"],
        enable_dossier=enable_dossier,
    )
    return render_script(engine)


def generate_variant(fixture: dict, variant: str, out_dir: str,
                     engine_factory: Callable, tts) -> dict:
    if variant == "human":
        text = fixture.get("human_transcript", "")
    elif variant == "with_dossier":
        text = _machine_text(fixture, True, engine_factory)
    elif variant == "no_dossier":
        text = _machine_text(fixture, False, engine_factory)
    else:
        raise ValueError(f"unknown variant: {variant}")

    vdir = Path(out_dir) / fixture["id"] / variant
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "text.txt").write_text(text, encoding="utf-8")
    synth_audio(tts, text, vdir / "audio.wav")
    return {"id": fixture["id"], "variant": variant, "text": text,
            "audio_path": str(vdir / "audio.wav")}
