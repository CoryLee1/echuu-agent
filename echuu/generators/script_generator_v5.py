"""ScriptGeneratorV5 — unit-based script generation in a single LLM call.

Replaces ScriptGeneratorV4. The single-call invariant preserves
unit-to-unit progression (U2 dialed up vs U1). See spec §2.2 / §2.3.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Protocol

from echuu.core.persona_model import PersonaModel
from echuu.core.unit import ScriptLine, Unit


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_PROMPT_TEMPLATE = """\
你为一个 5 分钟单人直播节目生成完整剧本。节目结构是固定的 4 个单元（钩-垫-翻）。
绝不写情绪标签或括号说明。 Filler（嗯/啊/那个）、停顿（——、…）必须写进 line.text。

人设锚（开拍前定，全程不变）：
- identity: {identity}
- belief:   {belief}
- flaw:     {flaw}
- visual_anchor: {visual_anchor}
- title_hook:    {title_hook}

话题：{topic}

4 个单元（这些字段你不能改，按结构填 lines）：
{units_json}

每单元产出 3-4 行，stage 取 hook/pad/turn 之一。每单元最后一行必须 stage='turn'。
单元间需要递进：U[1] 比 U[0] 更夸张；U[2] 信念外露；U[3] 弱点闪现（用占位文本也行）。

严格输出 JSON，结构：
{{
  "units": [
    {{
      "index": 0,
      "lines": [
        {{"id": "u0l0", "text": "...", "stage": "hook", "interruption_cost": 0.5}},
        {{"id": "u0l1", "text": "...", "stage": "pad",  "interruption_cost": 0.4}},
        {{"id": "u0l2", "text": "...", "stage": "turn", "interruption_cost": 0.8}}
      ]
    }},
    ...
  ]
}}
"""


def _strip_code_fence(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if m:
        return m.group(1)
    return raw


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("units"), list):
        return None
    return obj


class ScriptGeneratorV5:
    def __init__(self, llm: _LLM, example_sampler=None) -> None:
        self.llm = llm
        self.example_sampler = example_sampler  # PR 5.2 uses for fallback

    def _build_prompt(self, persona: PersonaModel, units: list[Unit], topic: str) -> str:
        # Serialize only the metadata LLM needs (axis/density/acoustic/rupture_slots)
        units_meta = [
            {
                "index": u.index,
                "time_window": list(u.time_window),
                "axis": u.axis,
                "density": u.density,
                "acoustic": asdict(u.acoustic),
                "rupture_slots": [
                    {"kind": r.kind, "nucleus_mode": r.nucleus_mode, "intensity": r.intensity}
                    for r in u.rupture_slots
                ],
            }
            for u in units
        ]
        return _PROMPT_TEMPLATE.format(
            identity=persona.identity,
            belief=persona.belief,
            flaw=persona.flaw,
            visual_anchor=persona.visual_anchor,
            title_hook=persona.title_hook,
            topic=topic,
            units_json=json.dumps(units_meta, ensure_ascii=False, indent=2),
        )

    def generate(self, persona: PersonaModel, units: list[Unit], topic: str = "") -> list[Unit]:
        prompt = self._build_prompt(persona, units, topic)
        raw = self.llm.generate(prompt)
        parsed = _parse(raw)

        if parsed is None or not self._is_complete(parsed, units):
            # Retry once
            raw = self.llm.generate(prompt)
            parsed = _parse(raw)

        if parsed is None or not self._is_complete(parsed, units):
            # Final degradation: fall back to placeholder content
            return self._fill_placeholder(units)

        # Apply LLM response into the planned units
        for u in units:
            u.lines = []
        index_to_unit = {u.index: u for u in units}
        for u_payload in parsed["units"]:
            idx = u_payload.get("index")
            if idx not in index_to_unit:
                continue
            target = index_to_unit[idx]
            for line in u_payload.get("lines", []):
                target.lines.append(ScriptLine(
                    id=str(line.get("id", f"u{idx}l{len(target.lines)}")),
                    text=str(line.get("text", "")),
                    stage=line.get("stage", "pad"),
                    is_rupture=False,
                    interruption_cost=float(line.get("interruption_cost", 0.5)),
                ))

        # Enforce: every unit's last line MUST be stage='turn' + is_rupture=True
        for u in units:
            if not u.lines:
                u.lines = self._placeholder_lines_for(u.index)
            last = u.lines[-1]
            last.stage = "turn"
            last.is_rupture = True

        return units

    def _is_complete(self, parsed: dict[str, Any], units: list[Unit]) -> bool:
        u_list = parsed.get("units", [])
        if len(u_list) != 4:
            return False
        for u in u_list:
            lines = u.get("lines", [])
            if len(lines) < 3:
                return False
        return True

    def _fill_placeholder(self, units: list[Unit]) -> list[Unit]:
        for u in units:
            u.lines = self._placeholder_lines_for(u.index)
            u.lines[-1].is_rupture = True
        return units

    def _placeholder_lines_for(self, idx: int) -> list[ScriptLine]:
        return [
            ScriptLine(id=f"u{idx}l0", text=f"[unit{idx} hook 占位]", stage="hook"),
            ScriptLine(id=f"u{idx}l1", text=f"[unit{idx} pad 占位]",  stage="pad"),
            ScriptLine(id=f"u{idx}l2", text=f"[unit{idx} turn 占位]", stage="turn"),
        ]
