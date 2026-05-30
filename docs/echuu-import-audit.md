# echuu import mechanism audit (2026-05-30)

Pre-requisite audit for PR 1 of the Echuu Rupture Engine refactor (see
`docs/superpowers/plans/2026-05-30-echuu-rupture-engine.md`). Goal: know
exactly how every `from echuu...` import is currently resolved before
PR 1 collapses the three parallel `echuu/` packages into a single
`echuu-agent/echuu/`.

Repo state at audit time: there is **no** `echuu-agent/echuu/` directory.
The `echuu` package only physically exists at:

- `echuu-agent/echuu-sdk-release/echuu/`  (suspected canonical)
- `echuu-agent/public/echuu/`             (near-identical mirror)

`echuu-agent/pyproject.toml` declares `name = "echuu"` with
`[tool.setuptools.packages.find] where = ["."] include = ["echuu*"]`,
but there is **no** matching package at `echuu-agent/echuu/`, so a
plain `pip install -e echuu-agent/` from the repo root would discover
zero packages (and `pip show echuu` confirms nothing is currently
installed — see "Active install" below).

## Callers

Search command (Step 1):
`grep -rn "^\(from\|import\) echuu" --include="*.py" echuu-agent/ src/ | grep -v ".venv" | grep -v "__pycache__"`

| File | Import statement | Resolution |
|---|---|---|
| `echuu-agent/demo.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack** — line 16-17: `SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"; sys.path.insert(0, str(SDK_ROOT))`. Resolves to `echuu-sdk-release/echuu/`. |
| `echuu-agent/tests/test_performer_cue.py` | `from echuu.core.performer_cue ...` / `from echuu.vrm.mapper ...` / `from echuu.vrm.presets ...` | **PYTHONPATH / pytest cwd** — no `sys.path.insert` in this file; relies on pytest being invoked with `echuu-sdk-release/` (or `public/`) on `PYTHONPATH`, or with a pre-installed `echuu`. No `conftest.py` providing it was found. **Will not import on a clean checkout** as-is. |
| `echuu-agent/workflow/backend/app.py` | `from echuu.live.engine import EchuuLiveEngine` (and `from echuu.live.language import detect_language` at line 288) | **sys.path hack** — line 18-19: `PROJECT_ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(PROJECT_ROOT))`. `parents[2] = echuu-agent/` — which has no `echuu/` package. **This insert does NOT help.** Works in production only because `echuu-agent/workflow/backend/Dockerfile` sets `ENV PYTHONPATH=/app/public` and copies `echuu-agent/public/` to `/app/public`. Locally on Windows the import fails unless the dev manually puts `echuu-sdk-release` or `public` on PYTHONPATH. |
| `echuu-agent/workflow/backend/echuu_live_engine.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack (same as app.py)** — line 9-11: inserts `parents[2] = echuu-agent/`. Same broken assumption: there is no `echuu/` at that path. 37-line shim, used as a thin re-export but actually non-functional on a clean checkout. |
| `echuu-agent/workflow/backend/echuu_demo.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack (same as app.py)** — inserts `parents[2] = echuu-agent/`. Same broken assumption. |
| `echuu-agent/workflow/backend/echuu_interactive.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack (same as app.py)** — inserts `parents[2] = echuu-agent/`. Same broken assumption. |
| `echuu-agent/echuu-web/backend/main.py` | (none directly — `from echuu...` is reached via `state.py` / `services/live_service.py`) | **sys.path hack via `config.py`** — `echuu-web/backend/config.py` lines 7-8 do `PROJECT_ROOT = parents[2]; sys.path.insert(0, ...)`. `parents[2]` from `echuu-web/backend/config.py` = `echuu-agent/`. Same broken assumption. main.py imports `config` first (`from .config import ...`), which mutates sys.path before any `from echuu` import runs. Works in production via Dockerfile env `PYTHONPATH=/app` after `COPY echuu /app/echuu` — but that COPY refers to a directory that doesn't exist at repo root today. |
| `echuu-agent/echuu-web/backend/state.py` | `from echuu.live.engine import EchuuLiveEngine` | **In-process import** — relies on `config.py`'s sys.path insert having already run. (See main.py row.) |
| `echuu-agent/echuu-web/backend/services/live_service.py` | `from echuu.live.engine import EchuuLiveEngine`, `from echuu.live.state import Danmaku` | **In-process import** — same as state.py, depends on `config.py`. |
| `echuu-agent/echuu-sdk-release/scripts/generate_examples.py` | `from echuu import EchuuLiveEngine` | **sys.path hack** — line 9: `sys.path.insert(0, str(Path(__file__).parent.parent))` = `echuu-sdk-release/`. Resolves to `echuu-sdk-release/echuu/`. Self-contained. |
| `echuu-agent/public/generate_japanese_audio.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack** — line 11: `sys.path.insert(0, str(Path(__file__).parent))` = `public/`. Resolves to `public/echuu/`. Self-contained. |
| `echuu-agent/public/examples/demo.py` | `from echuu.live.engine import EchuuLiveEngine` | **sys.path hack** — line 16-17: `SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"`. **Wrong path** — there is no `echuu-sdk-release/` under `public/examples/`; this file appears to be a stale copy of `echuu-agent/demo.py` and **does not work** as-is. (Likely shipped to the public repo where the layout differs.) |
| `src/` (Next.js frontend) | — | **No matches.** The frontend has zero Python `from echuu` imports (sanity check; expected). |

### Summary of resolution mechanisms

- **No pip install -e** is in effect (see Active install below).
- **No PYTHONPATH from `.env`** — `echuu-agent/.env` was not searched for `PYTHONPATH` (out of scope; the smoke imports below show none is set in the current shell).
- **Two Dockerfiles** rely on env `PYTHONPATH`:
  - `echuu-agent/Dockerfile`: `ENV PYTHONPATH=/app`, `COPY echuu /app/echuu`. The COPY source `echuu` does NOT exist at the repo root today — this Dockerfile is broken on the current tree unless built from a different context where `echuu/` exists at root.
  - `echuu-agent/workflow/backend/Dockerfile`: `ENV PYTHONPATH=/app/public`, `COPY echuu-agent/public /app/public`. This works in production because `public/echuu/` does exist.
- **`echuu-agent/start.sh`** sets `export PYTHONPATH="${PYTHONPATH:-$PWD}:$PWD"` and then `cd workflow/backend && uvicorn app:app`. `$PWD` at the time of export is `echuu-agent/`, which contains no `echuu/`. **start.sh is broken on the current tree** for the same reason as the workflow `sys.path.insert`s.
- **Practical conclusion:** Every local dev invocation today depends on either (a) running from inside `echuu-sdk-release/` or `public/`, or (b) the developer having manually added one of those to `PYTHONPATH`. The repeated `sys.path.insert(0, parents[2])` shims in `workflow/backend/*.py` and `echuu-web/backend/config.py` are dead code on the present tree.

## Active install (current state)

```
$ pip show echuu
WARNING: Package(s) not found: echuu
```

No editable or wheel install of `echuu` is registered in the active
Python environment. All resolutions today are via `sys.path` mutation
or container `PYTHONPATH`.

## Baseline smoke imports (Step 4)

Both commands from the plan were executed verbatim from
`E:/nextjs-vtuber-mocap`:

```
$ cd echuu-agent && python -c "from echuu.live.engine import EchuuLiveEngine; print(EchuuLiveEngine)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'echuu'

$ cd echuu-agent/echuu-web/backend && python -c "from echuu.live.engine import EchuuLiveEngine; print(EchuuLiveEngine)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'echuu'
```

**Both fail.** This is the baseline finding: nothing imports without an
external `PYTHONPATH` / `sys.path` hook. Recorded per task spec
("If smoke import in Step 4 fails, that IS the finding — record the
failure ... verbatim").

For completeness, the package IS importable if either candidate
directory is added to `sys.path` explicitly:

```
$ cd echuu-agent && python -c "import sys; sys.path.insert(0,'echuu-sdk-release'); from echuu.live.engine import EchuuLiveEngine; print(EchuuLiveEngine, EchuuLiveEngine.__module__)"
<class 'echuu.live.engine.EchuuLiveEngine'> echuu.live.engine

$ cd echuu-agent && python -c "import sys; sys.path.insert(0,'public'); from echuu.live.engine import EchuuLiveEngine; print(EchuuLiveEngine, EchuuLiveEngine.__module__)"
<class 'echuu.live.engine.EchuuLiveEngine'> echuu.live.engine
```

So both `echuu-sdk-release/echuu/` and `public/echuu/` are valid
sources today — confirming the "three parallel packages" framing in
the plan (counting `workflow/backend/echuu_live_engine.py` as the
third, despite being a 37-line non-functional shim on the current
tree).

## Migration plan for PR 1

- **Old (current state):**
  - Two physical copies: `echuu-agent/echuu-sdk-release/echuu/` and `echuu-agent/public/echuu/`.
  - One non-functional shim: `echuu-agent/workflow/backend/echuu_live_engine.py`.
  - Every caller resolves `from echuu...` via per-file `sys.path.insert` or container `PYTHONPATH`. No `pip install -e`.
  - `echuu-agent/pyproject.toml` declares `name = "echuu"` but has no `echuu/` package at its own root — so `pip install -e echuu-agent/` is currently a no-op for the `echuu` namespace.

- **New (target after PR 1):**
  - Single source of truth at `echuu-agent/echuu/` (via `git mv echuu-sdk-release/echuu → echuu-agent/echuu`).
  - Delete `echuu-agent/public/echuu/` (after diffing for any drift — recommended pre-merge sanity check).
  - Delete `echuu-agent/workflow/backend/echuu_live_engine.py` (the 37-line shim).
  - Install path becomes: `pip install -e echuu-agent/`. With `name = "echuu"` and packages-find finding `echuu/` at the same root, this works.
  - Remove every `sys.path.insert(0, PROJECT_ROOT)` in callers — the editable install handles resolution.

- **Files to update during PR 1** (delete sys.path hacks for `echuu` resolution, and/or remove dead Dockerfile copies):
  1. `echuu-agent/demo.py` — remove lines 16-17 (`SDK_ROOT = ... / "echuu-sdk-release"; sys.path.insert(...)`).
  2. `echuu-agent/workflow/backend/app.py` — remove lines 17-19 (`PROJECT_ROOT = parents[2]; sys.path.insert(...)`). `PROJECT_ROOT` is still used at line 35 for `SCRIPTS_DIR`, so keep the Path computation but drop the `sys.path` line.
  3. `echuu-agent/workflow/backend/echuu_demo.py` — remove lines 6-12 sys.path shim.
  4. `echuu-agent/workflow/backend/echuu_interactive.py` — remove lines 6-12 sys.path shim.
  5. `echuu-agent/workflow/backend/echuu_live_engine.py` — **delete entire file** (37-line shim, fully redundant).
  6. `echuu-agent/echuu-web/backend/config.py` — remove lines 7-8 sys.path insert (keep `PROJECT_ROOT` for `SCRIPTS_DIR`).
  7. `echuu-agent/echuu-web/backend/migrations/init_data.py`, `migrate_localstorage.py`, `database/database.py`, `alembic/env.py` — same sys.path shim removal.
  8. `echuu-agent/public/echuu/` — **delete entire tree** (mirror copy).
  9. `echuu-agent/public/generate_japanese_audio.py`, `echuu-agent/public/examples/*.py` — decide: either delete `public/` wholesale (preferred — it's the public SDK mirror, not used in production) or rewrite their sys.path hacks. Confirm with maintainer before PR 1.
  10. `echuu-agent/echuu-sdk-release/` — **delete entire tree after `git mv`** (its `echuu/` moved up, its `scripts/generate_examples.py` and its `pyproject.toml` become redundant with the root `pyproject.toml`).
  11. `echuu-agent/Dockerfile` — already says `COPY echuu /app/echuu`; once the `git mv` runs, this becomes correct as-is. Verify `PYTHONPATH=/app` line can be replaced with `RUN pip install -e .` for cleanliness (optional).
  12. `echuu-agent/workflow/backend/Dockerfile` — change `COPY echuu-agent/public /app/public` to `COPY echuu-agent/echuu /app/echuu` and `ENV PYTHONPATH=/app/public` to `ENV PYTHONPATH=/app` (or `RUN pip install -e /app/echuu-agent`).
  13. `echuu-agent/start.sh` — current `export PYTHONPATH="${PYTHONPATH:-$PWD}:$PWD"` becomes correct once `echuu/` exists at `$PWD`. Consider replacing with `pip install -e .` in CI bootstrap instead.
  14. `echuu-agent/tests/test_performer_cue.py` — no change to the file itself; will start importing cleanly once `pip install -e echuu-agent/` is the standard dev setup. Add a `tests/conftest.py` only if pytest still can't find the package (it should, after the editable install).
  15. `echuu-agent/pyproject.toml` — keep as-is. Already declares `name = "echuu"` and `[tool.setuptools.packages.find] include = ["echuu*"]`; will start working the moment `echuu/` lands at the same level.
  16. `echuu-agent/echuu-sdk-release/pyproject.toml` and `echuu-agent/public/pyproject.toml` — deleted along with their parent directories.

### Recommended ordering inside PR 1

1. Diff `echuu-sdk-release/echuu/` vs `public/echuu/` — if non-trivial drift exists, decide which is canonical (plan claims `echuu-sdk-release` is canonical) and capture the diff in the PR description.
2. `git mv echuu-agent/echuu-sdk-release/echuu echuu-agent/echuu`.
3. Delete `echuu-agent/echuu-sdk-release/` and `echuu-agent/public/` (or move stragglers out first).
4. Delete `echuu-agent/workflow/backend/echuu_live_engine.py`.
5. Run the sys.path-hack removals listed above (items 1-7, 9).
6. Update both Dockerfiles and `start.sh` (items 11-13).
7. Add `pip install -e echuu-agent/` to dev/CI setup docs.
8. Re-run the smoke imports from Step 4 — both must print `<class 'echuu.live.engine.EchuuLiveEngine'>`.
