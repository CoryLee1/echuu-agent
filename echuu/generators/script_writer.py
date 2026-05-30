"""ScriptWriter (agent②) — 综艺编剧，从故事内核创作 5 分钟剧本。

创作人格 = 詹仁雄 / 王伟忠（康熙来了幕后）级别的综艺编剧功力：金句精彩、故事有
活人感与综艺感、让人想截图做表情包。

不是「按 beat 填格子」——它拿 RichPersona + StoryCore + few-shot 真实片段，通盘规划
叙事（起承转合 / 钩 / 纠结 / 金句 / 碎碎念）并把内容连贯地落进 4 个时间/音色桶。

单次 LLM 调用 + 退化兜底。
See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §4.
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore
from echuu.core.unit import ScriptLine, Unit


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_PROMPT_TEMPLATE = """\
你是金牌综艺编剧（詹仁雄 / 王伟忠那一挂的功力）。给一个 5 分钟单人直播写完整剧本。
目标：金句精彩、故事有活人感和综艺感，让观众忍不住截图做表情包。

【这个人是谁】
- 身份：{identity}
- 信念：{belief}（会被现实打脸）
- 弱点：{flaw}
- 语癖（必须自然织进台词）：{verbal_tics}
- 情境弱点：{situational_weaknesses}
- 反差/悬疑：{contrast_hook}
- 生活化锚点（拿来做具体细节）：{life_anchors}

【今天讲什么 · 故事内核】
- 话题：{topic}
- 主线：{spine}
- 核心反差：{central_contrast}
- 情绪暗线：{emotional_undercurrent}
- 金句种子（打磨成真金句）：{punchline_seeds}
- 开场钩子角度：{hook_angle}

【真实主播是怎么讲话的（模仿这种活人节奏，不是抄内容）】
{examples}

【硬要求】
1. 前 60 秒内必须抛出钩子/爆梗，一上来就让人想留下。
2. 整体是**一个连贯的故事**，起承转合，段与段自然衔接——不是 4 段拼贴。
3. 自然用上这个人的语癖；写**碎碎念**（自我嘀咕、跑神）和**自我拉扯的纠结点**。
4. 生活化的**具体细节**：具体到身边的物品、与话题相关、对当时状况的实际描写。
5. 抖金句：至少几句让人想截图的话。
6. filler（嗯/那个/诶）和停顿（——、…）直接写进台词文本里。
7. 绝不写情绪标签或括号说明；绝不写「升华/总结人生道理」那种说教结尾。

【节奏护栏：4 个时间/音色桶（把故事铺进去，能量从高走到低）】
{unit_rails}

严格输出 JSON（不要任何额外文字、不要 markdown 围栏）：
{{
  "units": [
    {{"index": 0, "lines": [
      {{"text": "...", "interruption_cost": 0.5}},
      {{"text": "...", "interruption_cost": 0.4}}
    ]}},
    ... (共 4 个 unit，每个 3-4 行)
  ]
}}
"""


def _strip_fence(raw: str) -> str:
    raw = (raw or "").strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    return m.group(1) if m else raw


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(_strip_fence(raw))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("units"), list):
        return None
    return obj


def _join(items) -> str:
    if not items:
        return "（无）"
    return "、".join(str(i) for i in items)


class ScriptWriter:
    def __init__(self, llm: _LLM, example_sampler=None) -> None:
        self.llm = llm
        self.example_sampler = example_sampler

    def _unit_rails(self, units: list[Unit]) -> str:
        labels = ["开场/钩", "递进/铺垫", "缠结/纠结", "收束/翻转"]
        out = []
        for i, u in enumerate(units):
            t0, t1 = u.time_window
            label = labels[i] if i < len(labels) else f"段{i}"
            out.append(f"- Unit{i} [{int(t0)}-{int(t1)}s] {label}，能量={u.density}")
        return "\n".join(out)

    def _build_prompt(self, persona: RichPersona, core: StoryCore,
                      units: list[Unit], examples: str, topic: str) -> str:
        return _PROMPT_TEMPLATE.format(
            identity=persona.identity,
            belief=persona.belief,
            flaw=persona.flaw,
            verbal_tics=_join(persona.verbal_tics),
            situational_weaknesses=_join(persona.situational_weaknesses),
            contrast_hook=persona.contrast_hook or "（无）",
            life_anchors=_join(persona.life_anchors),
            topic=topic,
            spine=core.spine,
            central_contrast=core.central_contrast or "（无）",
            emotional_undercurrent=core.emotional_undercurrent or "（无）",
            punchline_seeds=_join(core.punchline_seeds),
            hook_angle=core.hook_angle or "（无）",
            examples=examples or "（无示例）",
            unit_rails=self._unit_rails(units),
        )

    def _try_generate(self, prompt: str) -> str | None:
        try:
            return self.llm.generate(prompt)
        except Exception as exc:
            print(f"[ScriptWriter] LLM 调用失败: {exc}")
            return None

    def write(self, persona: RichPersona, core: StoryCore, units: list[Unit],
              examples: str = "", topic: str = "") -> list[Unit]:
        prompt = self._build_prompt(persona, core, units, examples, topic)
        raw = self._try_generate(prompt)
        parsed = _parse(raw) if raw is not None else None

        if parsed is None or not self._is_complete(parsed, units):
            raw = self._try_generate(prompt)  # retry once
            parsed = _parse(raw) if raw is not None else None

        if parsed is None or not self._is_complete(parsed, units):
            return self._fill_placeholder(units)

        index_to_unit = {u.index: u for u in units}
        for u in units:
            u.lines = []
        for u_payload in parsed["units"]:
            idx = u_payload.get("index")
            if idx not in index_to_unit:
                continue
            target = index_to_unit[idx]
            for line in u_payload.get("lines", []):
                n = len(target.lines)
                target.lines.append(ScriptLine(
                    id=f"u{idx}l{n}",
                    text=str(line.get("text", "")).strip(),
                    stage=self._stage_for(n, len(u_payload.get("lines", []))),
                    is_rupture=False,  # 不再硬塞 rupture（弱点有机浮现）
                    interruption_cost=float(line.get("interruption_cost", 0.5)),
                ))
        for u in units:
            if not u.lines:
                u.lines = self._placeholder_lines_for(u.index)
        return units

    @staticmethod
    def _stage_for(idx: int, total: int) -> str:
        """软 stage 标注（仅供 TTS/前端节奏参考，不再驱动 rupture）。"""
        if idx == 0:
            return "hook"
        if idx >= total - 1:
            return "turn"
        return "pad"

    def _is_complete(self, parsed: dict[str, Any], units: list[Unit]) -> bool:
        u_list = parsed.get("units", [])
        if len(u_list) != len(units):
            return False
        for u in u_list:
            if len(u.get("lines", [])) < 2:
                return False
        return True

    def _fill_placeholder(self, units: list[Unit]) -> list[Unit]:
        for u in units:
            u.lines = self._placeholder_lines_for(u.index)
        return units

    def _placeholder_lines_for(self, idx: int) -> list[ScriptLine]:
        return [
            ScriptLine(id=f"u{idx}l0", text=f"[unit{idx} 开场 占位]", stage="hook"),
            ScriptLine(id=f"u{idx}l1", text=f"[unit{idx} 铺垫 占位]", stage="pad"),
            ScriptLine(id=f"u{idx}l2", text=f"[unit{idx} 收束 占位]", stage="turn"),
        ]
