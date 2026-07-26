"""三方变体生成：真人 transcript / 有扩充 / 无扩充，各产出 text + 一段 TTS wav。

机器变体驱动完整引擎（setup + run），拿 step 事件文本拼成整份剧本再整段合成音频，
保证评测台三栏都能试听、盲测不被"有没有音频"泄底。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from echuu.core.prompt_leakage import find_prompt_leaks


def render_script(engine, script_only: bool = False) -> str:
    """Render planned lines for eval, or drive runtime events for live simulation."""
    if script_only:
        state = getattr(engine, "state", None)
        lines = getattr(state, "script_lines", None)
        if isinstance(lines, list):
            return "\n".join(
                str(getattr(line, "text", "")).strip()
                for line in lines
                if str(getattr(line, "text", "")).strip()
            )
    lines = []
    # max_steps=15 caps machine variants at the production inline default (see
    # start-inline). This makes the `vs human` comparison length-biased (human
    # transcripts aren't capped), but the primary with_dossier vs no_dossier
    # ablation is symmetric — both machine variants share this same cap — so
    # the headline verdict (see pairwise.cmd_report) is unaffected.
    for ev in engine.run(max_steps=15, play_audio=False, save_audio=False):
        sp = (ev.get("speech") or ev.get("line", {}).get("text") or "").strip()
        if sp:
            lines.append(sp)
    return "\n".join(lines)


def synth_audio(tts, text: str, out_wav: Path) -> dict:
    started = perf_counter()
    audio = tts.synthesize(text) if text else b""
    out_wav.write_bytes(audio or b"")
    return {
        "duration_ms": round((perf_counter() - started) * 1000, 1),
        "audio_bytes": len(audio or b""),
        "text_chars": len(text),
    }


def stable_retrieval_seed(fixture: dict) -> int:
    """Pair all machine variants with the same deterministic retrieval draw."""
    source_id = fixture.get("source_fixture_id", fixture.get("id", ""))
    repeat = fixture.get("repeat", 1)
    payload = f"{source_id}\0{repeat}\0fewshot-v1"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:4], "big")


def _machine_text(fixture: dict, enable_dossier: bool, engine_factory: Callable) -> tuple[str, dict]:
    engine = engine_factory()
    source_id = fixture.get("source_fixture_id", fixture.get("id", ""))
    retrieval_seed = int(fixture.get("_retrieval_seed", stable_retrieval_seed(fixture)))
    allowed_ids = fixture.get("_retrieval_allowed_ids")
    engine.setup(
        name=fixture.get("character_name", "评测主播"),
        persona=fixture.get("persona", "普通、爱观察生活的直播主播"),
        background=fixture.get("background", ""),
        topic=fixture["topic"],
        enable_dossier=enable_dossier,
        retrieval_allowed_ids=allowed_ids,
        retrieval_exclude_ids=[source_id] if source_id else [],
        retrieval_seed=retrieval_seed,
        tuning_guidance=fixture.get("_tuning_guidance", []),
        tone_intent=fixture.get("tone_intent", "auto"),
        depth_budget=fixture.get("depth_budget", "auto"),
        entertainment_mechanism=fixture.get("entertainment_mechanism", ""),
    )
    started = perf_counter()
    call_start = len(getattr(getattr(engine, "llm_gen", None), "calls", []))
    text = render_script(engine, script_only=True)
    runtime_leaks = find_prompt_leaks(
        text, fixture.get("_tuning_guidance", []),
    )
    trace = getattr(engine, "debug_trace", {"version": 1, "stages": []})
    trace["evaluation_context"] = {
        "source_fixture_id": source_id,
        "split": fixture.get("split", "unspecified"),
        "retrieval_seed": retrieval_seed,
        "retrieval_allowed_pool_size": len(allowed_ids) if allowed_ids is not None else None,
        "retrieval_exclude_ids": [source_id] if source_id else [],
        "tuning_guidance_ids": [
            str(item.get("id", ""))
            for item in fixture.get("_tuning_guidance", [])
            if isinstance(item, dict) and item.get("id")
        ],
    }
    trace["stages"].append({
        "id": "runtime_output",
        "label": "运行输出",
        "status": "degraded" if runtime_leaks else "completed",
        "duration_ms": round((perf_counter() - started) * 1000, 1),
        "ai": (
            engine.llm_gen.summarize_since(call_start)
            if hasattr(getattr(engine, "llm_gen", None), "summarize_since")
            else {"uses_ai": False, "call_count": 0}
        ),
        "input": {
            "script_line_count": len(getattr(getattr(engine, "state", None), "script_lines", [])),
            "mode": "planned_script_only",
            "max_steps": 0,
        },
        "metrics": {
            "text_chars": len(text),
            "line_count": len(text.splitlines()),
            "prompt_leak_detected": bool(runtime_leaks),
            "prompt_leak_markers": list(runtime_leaks),
        },
        "output": {"text": text},
    })
    return text, trace


def generate_variant(fixture: dict, variant: str, out_dir: str,
                     engine_factory: Callable, tts,
                     metadata: dict[str, Any] | None = None) -> dict:
    if variant == "human":
        text = fixture.get("human_transcript", "")
        trace = {
            "version": 1,
            "pipeline": "human_reference",
            "stages": [
                {
                    "id": "input",
                    "label": "真人参考输入",
                    "status": "completed",
                    "duration_ms": 0,
                    "ai": {"uses_ai": False, "call_count": 0},
                    "output": {
                        "topic": fixture.get("topic", ""),
                        "character_name": fixture.get("character_name", ""),
                        "persona": fixture.get("persona", ""),
                        "tone_intent": fixture.get("tone_intent", "auto"),
                        "depth_budget": fixture.get("depth_budget", "auto"),
                        "entertainment_mechanism": fixture.get("entertainment_mechanism", ""),
                    },
                },
                {
                    "id": "runtime_output",
                    "label": "真人原稿",
                    "status": "completed",
                    "duration_ms": 0,
                    "ai": {"uses_ai": False, "call_count": 0},
                    "metrics": {"text_chars": len(text), "line_count": len(text.splitlines())},
                    "output": {"text": text},
                },
            ],
        }
    elif variant == "with_dossier":
        text, trace = _machine_text(fixture, True, engine_factory)
    elif variant == "no_dossier":
        text, trace = _machine_text(fixture, False, engine_factory)
    else:
        raise ValueError(f"unknown variant: {variant}")

    source_id = fixture.get("source_fixture_id", fixture.get("id", ""))
    allowed_ids = fixture.get("_retrieval_allowed_ids")
    trace.setdefault("evaluation_context", {
        "source_fixture_id": source_id,
        "split": fixture.get("split", "unspecified"),
        "retrieval_seed": stable_retrieval_seed(fixture),
        "retrieval_allowed_pool_size": len(allowed_ids) if allowed_ids is not None else None,
        "retrieval_exclude_ids": [source_id] if source_id else [],
        "tuning_guidance_ids": [
            str(item.get("id", ""))
            for item in fixture.get("_tuning_guidance", [])
            if isinstance(item, dict) and item.get("id")
        ],
    })

    vdir = Path(out_dir) / fixture["id"] / variant
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "text.txt").write_text(text, encoding="utf-8")
    audio_metrics = synth_audio(tts, text, vdir / "audio.wav")
    trace["stages"].append({
        "id": "tts",
        "label": "语音合成",
        "status": "completed" if audio_metrics["audio_bytes"] else "degraded",
        **audio_metrics,
        "input": {"text_chars": len(text)},
        "metrics": audio_metrics,
        "ai": {
            "uses_ai": bool(text),
            "provider": "DashScope",
            "model": os.getenv("TTS_MODEL", "qwen3-tts-flash-realtime"),
            "call_count": 1 if text else 0,
            "duration_ms": audio_metrics["duration_ms"],
            "failed_calls": 0 if audio_metrics["audio_bytes"] else (1 if text else 0),
        },
        "output": {"audio_path": str(vdir / "audio.wav")},
    })
    (vdir / "trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    run_metadata = {
        "fixture_id": fixture["id"],
        "source_fixture_id": fixture.get("source_fixture_id", fixture["id"]),
        "variant": variant,
        "repeat": fixture.get("repeat", 1),
        "evaluation_split": fixture.get("split", "unspecified"),
        "retrieval_seed": stable_retrieval_seed(fixture),
        "retrieval_allowed_pool_size": (
            len(fixture["_retrieval_allowed_ids"])
            if "_retrieval_allowed_ids" in fixture
            else None
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    (vdir / "metadata.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"id": fixture["id"], "variant": variant, "text": text,
            "audio_path": str(vdir / "audio.wav"), "metadata": run_metadata}
