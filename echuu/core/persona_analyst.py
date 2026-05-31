"""PersonaAnalyst (agent①) — 从用户设定推导 RichPersona + StoryCore。

单次 LLM 调用，输出严格 JSON 两块：
  - persona: 语癖 / 情境弱点 / 反差悬疑 / 生活化锚点 + 身份/信念/弱点
  - story:   主线 / 核心反差 / 情绪暗线 / 金句种子 / 钩子角度

绝不抛错崩 setup()——LLM 失败时退化到占位（flaw 永不为空）。
See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §3.
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_PROMPT = """\
你是综艺节目的「人物策划」。读完下面这位主播的设定，做两件事：
(1) 把他/她抽象成一个「好讲故事的人」——不是复述设定，而是挖出能让人忍不住听下去的活人细节；
(2) 提炼这个人在这个话题上「凭什么值得讲」的故事内核。

主播：{name}
人设：{persona}
背景：{background}
今天的话题：{topic}

严格输出 JSON（不要任何额外文字、不要 markdown 围栏）：
{{
  "persona": {{
    "identity": "<观众秒认的身份，一句话>",
    "belief": "<他挂在嘴边、会被现实打脸的信念，一句话>",
    "flaw": "<具体到一个场景的弱点/反常点，越具体越好，例：'一被夸就慌到转移话题'>",
    "verbal_tics": ["<语癖/口头禅，2-4个，例：'我跟你讲'、'对吧'、'那种感觉'>"],
    "situational_weaknesses": ["<情境弱点，1-3条，格式：'一遇到X就Y'>"],
    "contrast_hook": "<反差/悬疑：让观众'等下，这人怎么…'的张力，一句话>",
    "life_anchors": ["<与话题相关的具体物品/场景/习惯，2-4个，越具体越好，例：'工位上贴满便利贴'>"],
    "title_hook": "<像标题，让人划到不想走，<=30字>",
    "visual_anchor": "<贯穿性视觉锚，如配饰/小动作/背景物>"
  }},
  "story": {{
    "spine": "<主线：就讲【一件】具体的事，有具体的人/事/时间，不是抽象感悟。别贪多>",
    "core_struggle": "<主角围绕这件事的【核心纠结/矛盾点】——他真正在意、犹豫、想不通或最想吐槽的那一个点。这是故事的心脏>",
    "twist": "<这件事的【翻转/转折】：最意外、最炸、最值得讲的那一下。这是重头戏，必须精彩>",
    "central_contrast": "<这件事里最大的反差/悬念>",
    "emotional_undercurrent": "<情绪暗线：从什么情绪走到什么情绪>",
    "story_beats": [
      "<起：用具体场景/物品/心情把人带进这件事（这一拍负责铺，别急着翻）>",
      "<承：纠结/矛盾升级，把张力顶上去（仍是同一件事，往深里走）>",
      "<转：翻转/转折发生的【具体一刻】——全场最炸，对应上面的 twist>",
      "<合：这件事如何落地，留个具体画面或选择，不要喊口号升华>"
    ],
    "punchline_seeds": ["<金句种子，2-4个，粗胚即可，编剧会再打磨>"],
    "hook_angle": "<开场前30-60秒怎么抓人，一句话>"
  }}
}}

要点：story_beats 是【同一件事】的四个阶段（起承转合），围绕 core_struggle 推进、有跌宕起伏。
不是四件不同的事，也不是同一个点绕四遍。第 3 拍(转)=twist，是重头戏，要做到精彩。
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
    if not isinstance(obj, dict):
        return None
    if not isinstance(obj.get("persona"), dict) or not isinstance(obj.get("story"), dict):
        return None
    return obj


def _as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _placeholder(name: str, persona: str, topic: str) -> tuple[RichPersona, StoryCore]:
    head = (persona or name or "未提供").strip().splitlines()[0][:40]
    rp = RichPersona(
        identity=head or "[待补充身份]",
        belief="[待补充信念]",
        flaw="[待补充弱点]",                       # I4: 非空
        verbal_tics=("那个", "就是说"),
        situational_weaknesses=("一紧张就开始绕圈子",),
        contrast_hook="[待补充反差]",
        life_anchors=(topic or "[待补充生活细节]",),
        title_hook="[待补充开场钩]",
        visual_anchor="[待补充视觉锚]",
    )
    sc = StoryCore(
        spine=f"关于「{topic}」的一段亲身经历" if topic else "[待补充主线]",
        core_struggle="[待补充核心纠结]",
        twist="[待补充翻转]",
        central_contrast="[待补充反差]",
        emotional_undercurrent="[待补充情绪暗线]",
        story_beats=("起：[铺垫]", "承：[升级]", "转：[翻转]", "合：[落点]"),
        punchline_seeds=(),
        hook_angle="[待补充钩子]",
    )
    return rp, sc


class PersonaAnalyst:
    """从用户设定推导 RichPersona + StoryCore（单次 LLM 调用 + 退化兜底）。"""

    def analyze(
        self,
        name: str,
        persona: str,
        topic: str,
        background: str,
        llm: _LLM,
    ) -> tuple[RichPersona, StoryCore]:
        prompt = _PROMPT.format(
            name=name or "", persona=persona or "", background=background or "", topic=topic or "",
        )
        for _ in range(2):  # one retry
            try:
                raw = llm.generate(prompt)
            except Exception as exc:
                print(f"[PersonaAnalyst] LLM 调用失败: {exc}")
                continue
            obj = _parse(raw)
            if not obj:
                continue
            p, s = obj["persona"], obj["story"]
            identity = str(p.get("identity", "")).strip()
            belief = str(p.get("belief", "")).strip()
            flaw = str(p.get("flaw", "")).strip()
            if not (identity and belief and flaw):
                continue  # 三轴缺失 → 重试/退化
            rp = RichPersona(
                identity=identity,
                belief=belief,
                flaw=flaw,
                verbal_tics=_as_tuple(p.get("verbal_tics")),
                situational_weaknesses=_as_tuple(p.get("situational_weaknesses")),
                contrast_hook=str(p.get("contrast_hook", "")).strip(),
                life_anchors=_as_tuple(p.get("life_anchors")),
                title_hook=str(p.get("title_hook", "")).strip(),
                visual_anchor=str(p.get("visual_anchor", "")).strip(),
            )
            sc = StoryCore(
                spine=str(s.get("spine", "")).strip() or f"关于「{topic}」的经历",
                core_struggle=str(s.get("core_struggle", "")).strip(),
                twist=str(s.get("twist", "")).strip(),
                central_contrast=str(s.get("central_contrast", "")).strip(),
                emotional_undercurrent=str(s.get("emotional_undercurrent", "")).strip(),
                story_beats=_as_tuple(s.get("story_beats")),
                punchline_seeds=_as_tuple(s.get("punchline_seeds")),
                hook_angle=str(s.get("hook_angle", "")).strip(),
            )
            return rp, sc
        # 退化路径
        return _placeholder(name, persona, topic)
