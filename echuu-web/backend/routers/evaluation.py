"""Echuu 内容质量评测 API：多轮生成、盲测与消融报告。"""
from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from echuu.eval.generate import generate_variant
from echuu.eval.pairwise import VARIANTS, win_rate
from echuu.eval.tuning_guidance import compile_tuning_guidance
from echuu.live.engine import EchuuLiveEngine
from echuu.live.tts_client import TTSClient

try:
    from ..auth.auth import get_current_active_user
    from ..database.models import User
except ImportError:
    from auth.auth import get_current_active_user
    from database.models import User


router = APIRouter(prefix="/eval", tags=["evaluation"])
EVAL_DIR = Path(__file__).resolve().parents[3] / "echuu" / "eval"
RUNS_DIR = EVAL_DIR / "runs"
FIXTURES_FILE = EVAL_DIR / "fixtures.jsonl"
PERSONAS_FILE = EVAL_DIR / "personas.json"
JUDGMENTS_FILE = EVAL_DIR / "judgments.jsonl"
TUNING_NOTES_FILE = EVAL_DIR / "tuning_notes.jsonl"

_state_lock = threading.Lock()
_notes_lock = threading.Lock()
_judgments_lock = threading.Lock()
_generation_state = {
    "running": False,
    "completed": 0,
    "total": 0,
    "current": "",
    "error": None,
}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _fixtures() -> list[dict]:
    profiles = (
        json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
        if PERSONAS_FILE.exists()
        else {}
    )
    return [{**row, **profiles.get(row.get("id"), {})} for row in _read_jsonl(FIXTURES_FILE)]


def _all_pairs() -> list[tuple[str, str, str]]:
    pairs = []
    if not RUNS_DIR.exists():
        return pairs
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        present = [v for v in VARIANTS if (run_dir / v / "text.txt").exists()]
        for index, left in enumerate(present):
            for right in present[index + 1:]:
                pairs.append((run_dir.name, left, right))
    return pairs


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _rater_id(user: User) -> str:
    return str(
        getattr(user, "username", None)
        or getattr(user, "email", None)
        or getattr(user, "id", None)
        or "anonymous"
    )


def _judged_pairs(rater: Optional[str] = None) -> set[tuple[str, frozenset[str]]]:
    return {
        (row.get("fixture_id", ""), frozenset((row.get("variant_a"), row.get("variant_b"))))
        for row in _read_jsonl(JUDGMENTS_FILE)
        if rater is None or row.get("rater") == rater
    }


def _run_generation(fixture_ids: list[str], repeats: int) -> None:
    fixtures = _fixtures()
    selected = [fx for fx in fixtures if fx["id"] in fixture_ids]
    train_ids = [fx["id"] for fx in fixtures if fx.get("split", "train") == "train"]
    if not train_ids:
        train_ids = [fx["id"] for fx in fixtures]
    tuning_guidance = compile_tuning_guidance(
        _read_jsonl(TUNING_NOTES_FILE),
        train_ids,
    )
    try:
        tts = TTSClient()
        for fixture in selected:
            for repeat in range(1, repeats + 1):
                run_fixture = {
                    **fixture,
                    "source_fixture_id": fixture["id"],
                    "repeat": repeat,
                    "id": f"{fixture['id']}__r{repeat:02d}",
                    "_retrieval_allowed_ids": train_ids,
                    "_tuning_guidance": tuning_guidance,
                }
                for variant in VARIANTS:
                    with _state_lock:
                        _generation_state["current"] = f"{run_fixture['id']} / {variant}"
                    generate_variant(
                        run_fixture,
                        variant,
                        str(RUNS_DIR),
                        engine_factory=EchuuLiveEngine,
                        tts=tts,
                        metadata={"eval_repeats": repeats},
                    )
                    with _state_lock:
                        _generation_state["completed"] += 1
    except Exception as exc:
        with _state_lock:
            _generation_state["error"] = str(exc)
    finally:
        with _state_lock:
            _generation_state["running"] = False
            _generation_state["current"] = ""


class GenerateRequest(BaseModel):
    fixture_ids: list[str] = Field(min_length=1)
    repeats: int = Field(default=3, ge=1, le=5)


class JudgmentRequest(BaseModel):
    fixture_id: str
    variant_a: Literal["human", "with_dossier", "no_dossier"]
    variant_b: Literal["human", "with_dossier", "no_dossier"]
    winner: Literal["a", "b", "tie"]


class TuningNoteRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=120)
    variant: Literal["human", "with_dossier", "no_dossier"]
    stage_id: str = Field(min_length=1, max_length=80)
    observation: str = Field(min_length=1, max_length=4000)
    target_excerpt: str = Field(default="", max_length=4000)
    positive_feedback: str = Field(default="", max_length=4000)
    issue_feedback: str = Field(default="", max_length=4000)
    adjustment: str = Field(default="", max_length=4000)
    expected_effect: str = Field(default="", max_length=4000)
    feedback_type: Literal["positive", "issue", "mixed"] = "mixed"
    category: Literal[
        "strength",
        "world_knowledge",
        "fabricated_detail",
        "focus_drift",
        "persona",
        "logic",
        "style",
        "repetition",
        "safety",
        "other",
    ] = "other"
    severity: Literal["low", "medium", "high"] = "medium"
    status: Literal["planned", "applied", "validated", "reverted"] = "planned"


@router.get("/fixtures")
def list_fixtures(_: User = Depends(get_current_active_user)):
    return [
        {
            "id": fx["id"],
            "split": fx.get("split", "unspecified"),
            "topic": fx.get("topic", ""),
            "character_name": fx.get("character_name", "评测主播"),
            "persona": fx.get("persona", ""),
            "tone_intent": fx.get("tone_intent", "auto"),
            "depth_budget": fx.get("depth_budget", "auto"),
            "entertainment_mechanism": fx.get("entertainment_mechanism", ""),
            "transcript_chars": len(fx.get("human_transcript", "")),
        }
        for fx in _fixtures()
    ]


@router.get("/status")
def evaluation_status(current_user: User = Depends(get_current_active_user)):
    pairs = _all_pairs()
    judged = _judged_pairs(_rater_id(current_user))
    with _state_lock:
        generation = dict(_generation_state)
    return {
        "fixtures": len(_fixtures()),
        "run_groups": len({row[0] for row in pairs}),
        "pairs_total": len(pairs),
        "pairs_judged": len(judged),
        "pairs_pending": max(0, len(pairs) - len(judged)),
        "generation": generation,
    }


@router.get("/runs")
def list_pipeline_runs(_: User = Depends(get_current_active_user)):
    if not RUNS_DIR.exists():
        return []
    rows = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        variants = []
        for variant in VARIANTS:
            variant_dir = run_dir / variant
            trace_path = variant_dir / "trace.json"
            if not trace_path.is_file():
                continue
            metadata = _read_json(variant_dir / "metadata.json")
            trace = _read_json(trace_path)
            variants.append({
                "variant": variant,
                "generated_at_utc": metadata.get("generated_at_utc"),
                "stage_count": len(trace.get("stages", [])),
            })
        if variants:
            rows.append({"run_id": run_dir.name, "variants": variants})
    return rows


@router.get("/trace/{run_id}/{variant}")
def pipeline_trace(
    run_id: str,
    variant: Literal["human", "with_dossier", "no_dossier"],
    _: User = Depends(get_current_active_user),
):
    path = RUNS_DIR / run_id / variant / "trace.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Pipeline trace 不存在")
    trace = _read_json(path)
    if not trace:
        raise HTTPException(status_code=422, detail="Pipeline trace 无法解析")
    return trace


@router.get("/tuning-notes")
def list_tuning_notes(
    run_id: Optional[str] = None,
    variant: Optional[str] = None,
    stage_id: Optional[str] = None,
    _: User = Depends(get_current_active_user),
):
    rows = _read_jsonl(TUNING_NOTES_FILE)
    if run_id:
        rows = [row for row in rows if row.get("run_id") == run_id]
    if variant:
        rows = [row for row in rows if row.get("variant") == variant]
    if stage_id:
        rows = [row for row in rows if row.get("stage_id") == stage_id]
    return list(reversed(rows[-200:]))


@router.post("/tuning-notes")
def create_tuning_note(
    request: TuningNoteRequest,
    current_user: User = Depends(get_current_active_user),
):
    trace_path = RUNS_DIR / request.run_id / request.variant / "trace.json"
    if not trace_path.is_file():
        raise HTTPException(status_code=404, detail="对应的 Pipeline trace 不存在")
    trace = _read_json(trace_path)
    if request.stage_id not in {stage.get("id") for stage in trace.get("stages", [])}:
        raise HTTPException(status_code=404, detail="对应的 Pipeline 阶段不存在")
    record = {
        "id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author": getattr(current_user, "username", "unknown"),
        **request.model_dump(),
    }
    TUNING_NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _notes_lock:
        with TUNING_NOTES_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


@router.post("/generate")
def start_generation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_active_user),
):
    known_ids = {fx["id"] for fx in _fixtures()}
    unknown = sorted(set(request.fixture_ids) - known_ids)
    if unknown:
        raise HTTPException(status_code=404, detail=f"未知样本: {', '.join(unknown)}")
    with _state_lock:
        if _generation_state["running"]:
            raise HTTPException(status_code=409, detail="评测生成任务正在运行")
        _generation_state.update({
            "running": True,
            "completed": 0,
            "total": len(request.fixture_ids) * request.repeats * len(VARIANTS),
            "current": "",
            "error": None,
        })
    background_tasks.add_task(_run_generation, request.fixture_ids, request.repeats)
    return {"ok": True, "total": _generation_state["total"]}


@router.get("/next")
def next_pair(current_user: User = Depends(get_current_active_user)):
    judged = _judged_pairs(_rater_id(current_user))
    pending = [
        row for row in _all_pairs()
        if (row[0], frozenset((row[1], row[2]))) not in judged
    ]
    if not pending:
        return {"done": True}
    fixture_id, left, right = secrets.choice(pending)
    if secrets.randbits(1):
        left, right = right, left
    return {
        "done": False,
        "fixture_id": fixture_id,
        "a": {
            "variant": left,
            "text": (RUNS_DIR / fixture_id / left / "text.txt").read_text(encoding="utf-8"),
            "audio_url": f"/api/eval/audio/{fixture_id}/{left}",
        },
        "b": {
            "variant": right,
            "text": (RUNS_DIR / fixture_id / right / "text.txt").read_text(encoding="utf-8"),
            "audio_url": f"/api/eval/audio/{fixture_id}/{right}",
        },
    }


@router.post("/judge")
def submit_judgment(
    request: JudgmentRequest,
    current_user: User = Depends(get_current_active_user),
):
    if request.variant_a == request.variant_b:
        raise HTTPException(status_code=422, detail="左右变体不能相同")
    pair_key = (request.fixture_id, frozenset((request.variant_a, request.variant_b)))
    valid = {(fx, frozenset((a, b))) for fx, a, b in _all_pairs()}
    if pair_key not in valid:
        raise HTTPException(status_code=404, detail="评测对不存在")
    rater = _rater_id(current_user)
    with _judgments_lock:
        if pair_key in _judged_pairs(rater):
            raise HTTPException(status_code=409, detail="你已经标注过该评测对")
        JUDGMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with JUDGMENTS_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                **request.model_dump(),
                "rater": rater,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")
    return {"ok": True}


@router.get("/report")
def evaluation_report(_: User = Depends(get_current_active_user)):
    judgments = _read_jsonl(JUDGMENTS_FILE)
    comparisons = [
        ("with_dossier", "no_dossier"),
        ("with_dossier", "human"),
        ("no_dossier", "human"),
    ]
    return [
        {"variant_a": a, "variant_b": b, **win_rate(judgments, a, b)}
        for a, b in comparisons
    ]


@router.get("/audio/{fixture_id}/{variant}")
def evaluation_audio(
    fixture_id: str,
    variant: Literal["human", "with_dossier", "no_dossier"],
):
    path = RUNS_DIR / fixture_id / variant / "audio.wav"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="音频不存在")
    return FileResponse(path, media_type="audio/wav")
