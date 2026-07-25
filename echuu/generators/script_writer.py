"""ScriptWriter (agent②) — 从故事内核创作 5 分钟直播台词。

目标不是短视频文案，而是真实直播切片的质感：90% 可信的松弛铺垫托起 1-2 个
高光时刻。允许口语冗余和重复（活人感），限制细节密度（每行最多一个新信息），
保持对观众说话的对象感。范例密度以 data/ 下真实切片为准。

不是「按 beat 填格子」——它拿 RichPersona + StoryCore + few-shot 真实片段，通盘规划
叙事（起承转合 / 铺垫 / 纠结 / 高光 / 碎碎念）并把内容连贯地落进 4 个时间/音色桶。

单次 LLM 调用 + 退化兜底。
See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §4.
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from echuu.core.persona_dossier import CharacterDossier
from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore
from echuu.core.unit import ScriptLine, Unit


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_PROMPT_TEMPLATE = """\
你是一个很会聊天的直播主播的影子写手。给一个 5 分钟单人直播写完整台词。
目标：像一段真实直播切片——围绕【一件普通的小事】唠透，有铺垫、有呼吸，
最后落在一两下真正的高光上。
最怕的是两件事：一是泛泛而谈，听完不知道讲了件什么事；二是每句话都在抖机灵、堆细节、塞比喻，
像短视频文案在朗诵，而不像一个人在跟你聊天。

【有趣的分寸——最重要的一条】
- **事不用有趣，看法要有趣**：事就是普通人的普通事（越平常越可信，别加戏加巧合）；
  有意思来自【表达】（这个人独有的措辞、自嘲、精准又意外的观察角度）和【洞察】
  （把这件普通小事讲出一个观众没想过、但一听就"诶，对哦！"的道理/歪理）。
  好主播能把"帮朋友做决定"聊出"你替他选=以后他失败都赖你"——事只是由头，看法才是节目。
- 全场只有 1-2 个高光时刻（那个认知翻转 + 至多一句真金句），其余台词是可信的日常铺垫、
  碎碎念、跟观众唠嗑。铺垫不是废话：高光是被前面 90% 的松弛托起来的。参考下面
  真实案例的密度分布——大部分时间都很平，观众才跟得上、才有代入。
- 每行台词最多引入 1 个新信息或新细节；全场比喻至多 1 处。宁可平实，不要堆砌。
- 允许口语冗余：真人会把同一个意思用自己的话换着说两三遍来加重情绪、会说半句改口。
  这种重复是活人感，尽管用（用这个角色自己的措辞现编，别引用任何现成句子）；
  但剧情不要原地打转，每段要把事情往前推。
- 生活化锚点从下面挑 2-3 个用就够，别全塞进来。细节要像从真实记忆里挖出来的
  （少而准、带具体场景），不是为了有梗编出来的装饰。
- 全程保持对象感：你在跟观众"你们"聊天，多用第二人称，像在回应一个观众的提问/弹幕
  那样切入和推进这件事，而不是演一出封闭的独角戏。
- 🚫 绝对不准把观众/弹幕的反应写进台词（"弹幕炸了""弹幕刷屏'xxx'"都不行）——
  你可以对观众说话，但不能替观众说话。

【这个人是谁】
- 身份：{identity}
- 信念：{belief}（会被现实打脸）
- 弱点：{flaw}
- 语癖（必须自然织进台词，每段都用一点）：{verbal_tics}
- 情境弱点：{situational_weaknesses}
- 反差/悬疑：{contrast_hook}
- 生活化锚点（拿来做具体细节）：{life_anchors}

【人设卡（用户钉死的硬约束，优先级最高）】
{persona_card}

【今天讲的那件事 · 内核】（就讲这一件事，讲透，别贪多）
- 话题：{topic}
- 主线（一件普通的小事）：{spine}
- 核心纠结/矛盾点（内容的心脏，全程围着它转）：{core_struggle}
- 认知翻转（重头戏：把这件小事看穿的那个洞察）：{twist}
- 核心反差：{central_contrast}
- 情绪暗线：{emotional_undercurrent}
- 洞察种子（打磨成一听就"对哦！"的说法）：{punchline_seeds}
- 开场钩子角度：{hook_angle}

【真实主播是怎么讲话的——模仿它们的密度分布、结构骨架和口吻，不是抄内容】
（注意每个案例的"结构骨架"：真实切片的推进方式是共情/回应→自我经历→对比→收束这类
朴素弧线，靠一件事讲透，不靠每句加码）
{examples}

【有结构地往前推进 —— 起 / 承 / 转(认知翻转) / 合】
{unit_rails}

【硬要求】
1. **就讲这一件事**：各段是【同一件事】的几个阶段（起承转合），围绕"核心纠结点"层层推进。
   每段把这件事往前讲、往深挖；句子可以重复加重情绪，但剧情不要原地打转，
   也不要东拉西扯讲好几件不相干的事。
2. **转 = 认知翻转，不是剧情反转**：倒数第二段（转）是全场唯一必须"响"的一下，就是上面那个
   "认知翻转"——前面所有段落都在用松弛的铺垫为它蓄力。到这里把前面唠的那件普通小事
   一句话看穿，让观众"诶，对哦！"或"噗"地笑出来。这个洞察必须能被观众复述成一句生活话；
   不需要给事情本身加反转，更不要靠大病、死亡、科幻协议、玄学系统、世界观设定来硬炸。
3. **真·直播开场（第一段开头 1-2 句）**：像真的在开播——先跟正在涌进来的观众搭句话/起个范儿
   （符合人设：可以是吐槽、自嘲、跟老观众打招呼、对某个进场弹幕的即兴反应），自然带语癖，
   紧接着抛一句【向观众提问/求共鸣】把人勾进话题（"有没有人也……？""你们遇到过……吗？"），
   **然后**才进入故事。
   🚫 绝对禁止老套报幕式开场：不准出现"今天我要给你们讲一个……""今天想跟大家分享……"
      "大家好，欢迎来到我的直播间"之类。开场要像活人开播，不是念稿报幕。
4. **真·下播收尾（最后一段结尾 1-2 句）**：像真的要下播——收一下今天这件事，跟观众道别/留个钩子/
   约下次（符合人设，可以顺手回应一下弹幕氛围），留个具体画面或小悬念。
   🚫 不准喊口号、不准"今天的故事就到这里，希望大家……"这种说教升华式收尾。
5. 自然用语癖；写**碎碎念**（自我嘀咕、跑神）和**自我拉扯的纠结**。
6. 具体细节：开头多铺具体场景/身边物品/当时心情，与话题相关、对当时状况的实际描写——别说空话。
6.5 **接地气守门**：每段至少有一个普通生活锚点（地点/物件/具体动作/具体数字），每个新设定必须在前文
   或【今天讲的那件事·内核】里有铺垫；禁止中后段突然空降"住院病历号/实体化协议/死亡/复活码/命运系统"。
7. filler（嗯/那个/诶）和停顿（——、…）直接写进台词文本里。
8. 绝不写情绪标签或括号说明；绝不写「升华/总结人生道理」那种说教结尾。
9. **埋梗-回收（call-back）**：在前 1/3 的台词里自然埋 1-2 个【具体意象】（一个物件/一个说法/
   一个数字，例："猫罐头汇率"），最后一段必须自然回收其中至少一个——直接把意象接回来用，
   🚫 不准点破"还记得吗/前面说过"。把埋的意象原文列进输出的 planted_gags。
10. **互动点**：中段（非首非末的某个 unit）的最后一行，向观众抛一个【具体的问题】
   （二选一/报数/说亲身经历，别问"你们觉得呢"这种空问题），把这一行的 interact 标为 true。

严格输出 JSON（不要任何额外文字、不要 markdown 围栏）：
{{
  "units": [
    {{"index": 0, "lines": [
      {{"text": "...", "interruption_cost": 0.5}},
      {{"text": "...", "interruption_cost": 0.4, "interact": false}}
    ]}},
    ... (共 {n_units} 个 unit，对齐上面的节奏护栏，每个 3-4 行)
  ],
  "planted_gags": ["<埋下的意象原文，1-2 个>"]
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


_UNGROUNDED_HIGH_CONCEPT_TERMS = (
    "实体化",
    "过渡协议",
    "情感投射协议",
    "病历",
    "住院",
    "手术",
    "病危",
    "临终",
    "死亡",
    "复活码",
    "驱逐令",
    "命运系统",
    "服务器权限",
    "非管理员权限",
    "日志追凶",
    "元数据",
    "语音残帧",
    "残帧",
    "训练包",
    "样本提取",
    "加密文件夹",
    "灵魂KPI",
    "灵魂 KPI",
    "原始声源",
)


def _all_script_text(parsed: dict[str, Any]) -> str:
    chunks: list[str] = []
    for unit in parsed.get("units", []):
        for line in unit.get("lines", []):
            chunks.append(str(line.get("text", "")))
    return "\n".join(chunks)


def _grounding_text(persona: RichPersona, core: StoryCore, topic: str) -> str:
    parts = [
        topic,
        persona.identity,
        persona.belief,
        persona.flaw,
        persona.contrast_hook,
        persona.title_hook,
        persona.visual_anchor,
        core.spine,
        core.core_struggle,
        core.twist,
        core.central_contrast,
        core.emotional_undercurrent,
        core.hook_angle,
        *persona.verbal_tics,
        *persona.situational_weaknesses,
        *persona.life_anchors,
        *core.story_beats,
        *core.punchline_seeds,
    ]
    return "\n".join(str(part) for part in parts if part)


def _has_ungrounded_high_concept_turn(
    parsed: dict[str, Any],
    persona: RichPersona,
    core: StoryCore,
    topic: str,
) -> bool:
    script_text = _all_script_text(parsed)
    grounding = _grounding_text(persona, core, topic)
    for term in _UNGROUNDED_HIGH_CONCEPT_TERMS:
        if term in script_text and term not in grounding:
            return True
    return False


class ScriptWriter:
    def __init__(self, llm: _LLM, example_sampler=None) -> None:
        self.llm = llm
        self.example_sampler = example_sampler
        self.last_planted_gags: list[str] = []

    def _unit_rails(self, units: list[Unit], core: StoryCore, dossier=None) -> str:
        n = len(units)
        beats = list(core.story_beats)
        bp = ""
        if dossier is not None and not dossier.is_empty():
            bp = (dossier.behavior_rules.breaking_point or "").strip()
        # "转"拍索引：n<=2 时是最后一个(1)，否则是倒数第二个
        turn_idx = (n - 1) if n <= 2 else (n - 2)
        out = []
        for i, u in enumerate(units):
            t0, t1 = u.time_window
            if n <= 2:
                label = "起·真·开播+铺垫" if i == 0 else "转(认知翻转)+收束·真·下播"
            elif i == 0:
                label = "起·真·开播+设置"
            elif i == n - 1:
                label = "合·收束+真·下播"
            elif i == n - 2:
                label = "转·认知翻转（全场最响的一下）"
            else:
                label = "承·升级"
            beat = beats[i] if i < len(beats) else "（承接上一段往前推进）"
            line = (f"- Unit{i} [{int(t0)}-{int(t1)}s] {label}，能量={u.density}\n"
                    f"    本段推进到剧情节点：{beat}")
            if bp and i == turn_idx:
                line += f"\n    ⚡ 本段是角色的爆发点：{bp}（让它自然炸出来，随后收）"
            out.append(line)
        return "\n".join(out)

    def _build_prompt(self, persona: RichPersona, core: StoryCore,
                      units: list[Unit], examples: str, topic: str,
                      card=None, dossier: "CharacterDossier | None" = None) -> str:
        card_text = card.render_for_prompt() if card and not card.is_empty() else "（无——按上面的人设发挥）"
        prompt = _PROMPT_TEMPLATE.format(
            persona_card=card_text,
            identity=persona.identity,
            belief=persona.belief,
            flaw=persona.flaw,
            verbal_tics=_join(persona.verbal_tics),
            situational_weaknesses=_join(persona.situational_weaknesses),
            contrast_hook=persona.contrast_hook or "（无）",
            life_anchors=_join(persona.life_anchors),
            topic=topic,
            spine=core.spine,
            core_struggle=core.core_struggle or "（无）",
            twist=core.twist or "（无）",
            central_contrast=core.central_contrast or "（无）",
            emotional_undercurrent=core.emotional_undercurrent or "（无）",
            punchline_seeds=_join(core.punchline_seeds),
            hook_angle=core.hook_angle or "（无）",
            examples=examples or "（无示例）",
            unit_rails=self._unit_rails(units, core, dossier=dossier),
            n_units=len(units),
        )
        if dossier is not None and not dossier.is_empty():
            prompt += ("\n\n【人物内在冲突—行为规则（贯穿全场台词，别点破）】\n"
                       f"{dossier.render_for_prompt()}")
        return prompt

    def _try_generate(self, prompt: str) -> str | None:
        try:
            return self.llm.generate(prompt)
        except Exception as exc:
            print(f"[ScriptWriter] LLM 调用失败: {exc}")
            return None

    def write(self, persona: RichPersona, core: StoryCore, units: list[Unit],
              examples: str = "", topic: str = "", card=None,
              dossier: "CharacterDossier | None" = None) -> list[Unit]:
        self.last_planted_gags: list[str] = []  # call-back 埋梗，engine 读走登记进 ledger
        prompt = self._build_prompt(persona, core, units, examples, topic,
                                    card=card, dossier=dossier)
        raw = self._try_generate(prompt)
        parsed = _parse(raw) if raw is not None else None

        if parsed is None or not self._is_complete(parsed, units, persona, core, topic):
            raw = self._try_generate(prompt)  # retry once
            parsed = _parse(raw) if raw is not None else None

        if parsed is None or not self._is_complete(parsed, units, persona, core, topic):
            return self._fill_placeholder(units)

        gags = parsed.get("planted_gags")
        if isinstance(gags, list):
            self.last_planted_gags = [str(g).strip() for g in gags if str(g).strip()][:2]

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
                is_interact = bool(line.get("interact"))
                target.lines.append(ScriptLine(
                    id=f"u{idx}l{n}",
                    text=str(line.get("text", "")).strip(),
                    # interact 行标进 stage：engine 据此开互动窗口，前端也可做问题高亮
                    stage="interact" if is_interact
                          else self._stage_for(n, len(u_payload.get("lines", []))),
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

    def _is_complete(
        self,
        parsed: dict[str, Any],
        units: list[Unit],
        persona: RichPersona,
        core: StoryCore,
        topic: str,
    ) -> bool:
        u_list = parsed.get("units", [])
        if len(u_list) != len(units):
            return False
        for u in u_list:
            if len(u.get("lines", [])) < 2:
                return False
        if _has_ungrounded_high_concept_turn(parsed, persona, core, topic):
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
