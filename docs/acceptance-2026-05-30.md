# echuu Rupture Engine — Acceptance Report

- **Plan:** `docs/superpowers/plans/2026-05-30-echuu-rupture-engine.md`
- **Spec:** `docs/superpowers/specs/2026-05-30-echuu-rupture-engine-design.md`
- **Run date:** 2026-05-31
- **Branch:** `refactor/rupture-engine` (echuu-agent submodule)

## Hard indicators (spec §9)

- [x] PR 0–8 implemented (PR 0–6 committed earlier; PR 7 backend + FE; PR 8 here).
- [x] `tests/` green: `python -m pytest tests/ -q` → **66 passed**.
- [x] `ECHUU_LLM_PROVIDER=claude python demo.py --acceptance` runs end-to-end with
      **real LLM-generated content** (Anthropic Claude) + real Qwen-TTS audio.
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

- **5-min MP3 (real content):** `output/scripts/20260531_032232_小梅_转行_6_个月的真实体感_live.mp3`
  (1.2 MB, 12 segments merged). Acoustic profile descends across units (U1 highest
  pitch/rate, U4 lowest) — segment-to-segment difference is audible.
- **PersonaModel extraction:** `flaw = "辞职那天哭了一整夜，其实内心很脆弱不安"` — extracted
  by the LLM from the persona text, then carried through to Unit[4].
- **U4 flaw rupture:** `nucleus_mode = choice_cost` (StructureBreaker keyword-matched "辞职"),
  final `turn` line `is_rupture=True`:
  > 但我想说的是——脆弱不丢人，真正的勇敢就是带着恐惧继续走下去
  And U4's opener lands the vulnerable beat: "说到这里...我想起辞职那天晚上，我其实哭了一整夜".
- **Frontend progress:** `LiveUnitProgress` renders top-center while
  `streamState === 'performing'`, with unit pips + `Unit N/total · axis · L#` and a
  `✦` marker on flaw-rupture lines.

## LLM provider note

The live run succeeded with **Anthropic Claude** (`ECHUU_LLM_PROVIDER=claude`). Provider
availability observed in this dev environment:

| Provider | Status |
|---|---|
| Anthropic Claude (`claude-sonnet-4`) | ✅ working (used for this acceptance run) |
| Gemini (`gemini-3-flash-preview`) | ❌ `400 FAILED_PRECONDITION: User location is not supported` (geo-block) |
| OpenAI | ❌ `NotImplementedError` — client not implemented in `llm_factory.py` |

```bash
cd echuu-agent
ECHUU_LLM_PROVIDER=claude python demo.py --acceptance
```

The spec §5 degradation path (placeholder script + real TTS) was also verified earlier when
no provider was reachable — a provider outage degrades gracefully instead of crashing
`engine.setup()`.

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
- Add **Doubao (豆包) via 火山引擎 / Volcano Engine** as a bottom-tier LLM fallback in
  `llm_factory.py` (planned, pending Volcano Engine access).
- Gemini is geo-blocked in this environment; needs a VPN/region to use as a provider.
- `test_step_event_schema.py` lives in `tests/` rather than the planned
  `echuu-web/backend/tests/` — harmless, but note the divergence from the plan.
