# echuu Rupture Engine — Acceptance Report

- **Plan:** `docs/superpowers/plans/2026-05-30-echuu-rupture-engine.md`
- **Spec:** `docs/superpowers/specs/2026-05-30-echuu-rupture-engine-design.md`
- **Run date:** 2026-05-31
- **Branch:** `refactor/rupture-engine` (echuu-agent submodule)

## Hard indicators (spec §9)

- [x] PR 0–8 implemented (PR 0–6 committed earlier; PR 7 backend + FE; PR 8 here).
- [x] `tests/` green: `python -m pytest tests/ -q` → **66 passed**.
- [x] `python demo.py --acceptance` runs without errors (LLM-degraded — see note).
- [x] Output JSON `output/example_runs/demo_show.json` — 4 units; axes
      `["identity","belief","belief","flaw"]`; density `["high","high","medium","low"]`;
      Unit[3] carries a `flaw` rupture; Unit[3] last line `stage="turn"`, `is_rupture=True`.
- [x] Per-unit acoustic curve present: `pitch_rate = [1.10, 1.05, 0.92, 0.88]`
      (excited → serious → vulnerable), one `tts.update_session(...)` per unit.
- [x] Frontend reads v2 nested `step` schema (`src/hooks/use-echuu-websocket.ts`)
      and shows `Unit N/4 · axis · line M` (`LiveUnitProgress` in `VTuberLayout`).
- [x] Single `echuu/` source of truth — `find echuu-agent -type d -name echuu`
      (excluding `.venv`/`__pycache__`) returns exactly one path.

## Soft indicators

- **5-min MP3:** `output/scripts/20260531_030235_小梅_转行_6_个月的真实体感_live.mp3`
  (404 KB, 12 segments merged). Acoustic profile descends across units
  (U1 highest pitch/rate, U4 lowest) — segment-to-segment difference is audible.
- **U3 flaw line:** content was the degraded placeholder (`[unit3 turn 占位]`) because no
  live LLM was reachable (see note); the *structure* — flaw rupture on the final turn —
  is correct and verified.
- **Frontend progress:** `LiveUnitProgress` renders top-center while
  `streamState === 'performing'`, with unit pips + `Unit N/total · axis · L#` and a
  `✦` marker on flaw-rupture lines.

## ⚠️ LLM provider note (live run blocker)

A true live run with real LLM-generated script content could **not** be completed in this
environment — all three configured providers were externally unavailable:

| Provider | Status |
|---|---|
| Gemini (`gemini-3-flash-preview`) | `400 FAILED_PRECONDITION: User location is not supported for the API use` (geo-block) |
| Anthropic Claude (`claude-sonnet-4`) | `400 invalid_request_error: This organization has been disabled` |
| OpenAI | `NotImplementedError` — client not implemented in `llm_factory.py` |

Qwen TTS (DashScope) **is** reachable and was used to render real audio. The acceptance
run therefore exercised the **full engine + TTS pipeline with the spec §5 degradation
path** (placeholder script lines), proving structure + acoustic switching end-to-end.
Re-run with a reachable LLM (VPN for Gemini, an enabled Anthropic org, or an implemented
OpenAI client) to populate real line content:

```bash
cd echuu-agent
ECHUU_LLM_PROVIDER=claude python demo.py --acceptance   # or gemini / (openai once impl'd)
```

## Fixes made during acceptance

1. **LLM interface mismatch (real bug).** `PersonaModel.from_persona_text` and
   `ScriptGeneratorV5.generate` assumed an `llm.generate(prompt)` contract (matching their
   `FakeLLM` unit-test stubs), but real clients only expose `.call(prompt, ...)`. Added
   `_LLMGenerateAdapter` at the engine boundary (`echuu/live/engine.py`) bridging
   `.generate → .call(max_tokens=8000)`, keeping the V5 modules client-agnostic and the
   unit tests intact.
2. **Degradation gap (spec §5).** Both modules only caught malformed JSON, not LLM *call*
   exceptions — so a provider outage crashed `setup()` instead of degrading. Wrapped the
   `llm.generate(...)` calls so an API failure falls through to the placeholder path.
   This is exactly what let the acceptance run complete despite the LLM being down.

## Known gaps / V2 follow-ups

- Implement the OpenAI client in `llm_factory.py` (currently `NotImplementedError`).
- Re-run acceptance with a reachable LLM and append the real U3 flaw line + an A/B note
  on acoustic feel with genuine content.
- `test_step_event_schema.py` lives in `tests/` rather than the planned
  `echuu-web/backend/tests/` — harmless, but note the divergence from the plan.
