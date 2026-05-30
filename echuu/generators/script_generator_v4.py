"""
ScriptGeneratorV4 - 整合所有新组件的主生成器
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from ..core.trigger_bank import TriggerBank
from ..core.digression_db import DigressionDB
from ..core.structure_breaker import StructureBreaker
from ..core.emotion_mixer import EmotionMixer
from ..core.story_nucleus import StoryNucleus
from ..core.performer_cue import (
    PerformerCue,
    EmotionCue,
    GestureCue,
    LookCue,
    BlinkCue,
    LipsyncCue,
    EmotionKey,
    LookTarget,
    BlinkMode,
    infer_emotion_from_text,
)
from ..vrm.presets import get_gesture_for_stage, GESTURE_PRESETS


@dataclass
class ScriptLineV4:
    """V4 剧本台词"""

    id: str
    text: str
    stage: str
    interruption_cost: float
    key_info: List[str] = field(default_factory=list)
    disfluencies: List[str] = field(default_factory=list)
    emotion_break: Optional[Dict] = None

    trigger_type: str = "thought_drift"
    is_digression: bool = False
    has_digression: bool = False
    emotion_config: Optional[Dict] = None

    # 新增：表演标注
    cue: Optional[PerformerCue] = None

    def cue_to_dict(self) -> Optional[Dict[str, Any]]:
        """将 cue 转换为可序列化的字典"""
        return self.cue.to_dict() if self.cue else None


class ScriptGeneratorV4_1:
    """
    剧本生成器 V4.1

    核心改进：
    1. 多样化触发开场
    2. 真正的跑题注入
    3. 结构破坏（删除升华、非闭合结尾）
    4. 情绪复合
    5. 故事内核（分享欲 + 反常 + 内心戏）
    """

    SYSTEM_PROMPT_V4 = '''你是一个模拟直播主播"边想边说"的生成器。

## ⚠️ 核心认知

你不是在"写故事"，你是在模拟一个正在回忆的人的大脑。

### 真人 vs AI 的区别

| AI写作（❌） | 真人说话（✅） |
|-------------|---------------|
| 完整弧线，每句推进 | 碎片化，可中断 |
| 假跑题服务于铺垫 | 真跑题，要拉回来 |
| "500日元" | "几百日元吧" |
| "这件事让我明白..." | "就这样，我看弹幕" |
| 单一纯净情绪 | 复合情绪，用A包装B |

---

## 🧠 记忆提取模拟

回忆时信息这样浮现：
- 先画面/感觉，再细节
- 数字和时间最先模糊
- 会突然想起无关的事
- 会怀疑自己记错

**表现：**
```
❌ "2019年3月15日，500日元"
✅ "19年？20年？反正春天吧，几百日元来着"
```

---

## 🌀 思维漂移

说话时脑子会跑：
- A想起B，B想起C
- 有时拉回来，有时忘了
- "诶我说到哪了"是真不记得

**表现：**
```
❌ 每句都推进主线
✅ "汇率多少来着，七块多...现在才四块八，差太远了...诶说到哪了？对，腰果"
```

---

## 😭😂 情绪复合

真实情绪不单一：
- 感动+不好意思
- 生气+自嘲
- 用愤怒掩盖脆弱
- 用抱怨表达宠溺

**表现：**
```
❌ "我非常感动"
✅ "我就...不知道说什么，又想哭又觉得自己傻"
✅ "臭猫猫白嫖失败"（抱怨=宠溺）
```

---

## ⏸️ 可中断性

真人随时可能：
- 被弹幕/环境打断
- 自己放弃
- 忘记要说什么
- 草草收尾

**结尾不升华：**
```
❌ "这让我明白，人与人之间..."
✅ "好了不说了，SC有人问什么"
✅ "反正就这么个事"
```

---

## 📋 输出格式

生成8-10个叙事单元，JSON数组：

```json
[
  {
    "id": "line_0",
    "text": "口语内容（80-120字）",
    "stage": "Hook/Build-up/Climax/Resolution",
    "cost": 0.3,
    "key_info": ["关键点1"],
    "disfluencies": ["数字模糊", "自我修正"],
    "emotion_break": null
  }
]
```

### disfluencies 可选值
- "数字模糊": 不确定数字
- "自我修正": 说错后纠正
- "词语重复": 自然卡壳（不是设计感重复）
- "思路中断": 跑题或忘词
- "跑题细节": 无关但真实的细节
- "严重跑题": 50字+跑题然后拉回

    ### 必须做到
1. **体现分享欲**（为什么现在要说）
2. **数字可以模糊**（不要精确）
3. **不要升华结尾**
4. **情绪要复合**
5. **要有反常点/戏剧冲突**
6. **可以有轻微跑题，但必须是为了吊胃口或增加真实感，不要影响主线节奏**
'''

    NUCLEUS_PROMPT_TEMPLATE = """## 🎯 这个故事的内核

### 分享欲：为什么要说这个？
{sharing_urge_description}

开场方式（意图）：{opening_template}

### 反常点/戏剧性：为什么劲爆？
{abnormality_description}

### 故事结构：
{structure}

### 关键问题（必须想清楚再写）：
{key_prompts}

---

## ⚠️ 重要提醒

1. **八卦要劲爆** - 重点在于反差和不为人知的细节。
2. **减少无意义跑神** - 说话可以碎，但故事主线要清晰，不要让观众觉得你在梦游。
3. **内心戏 > 事件** - 体现你听到八卦时的震惊和纠结。
"""

    def __init__(self, llm, example_sampler=None):
        self.llm = llm
        self.example_sampler = example_sampler

        self.trigger_bank = TriggerBank()
        self.digression_db = DigressionDB()
        self.structure_breaker = StructureBreaker(self.digression_db)
        self.emotion_mixer = EmotionMixer()
        self.story_nucleus = StoryNucleus()

    def generate(
        self,
        name: str,
        persona: str,
        background: str,
        topic: str,
        language: str = "zh",
        character_config: dict = None,
        on_phase_callback: Optional[callable] = None,
    ) -> List[ScriptLineV4]:
        """
        V4 生成流程
        """

        def log_phase(phase, details=None):
            msg = f"{phase}"
            if details:
                msg += f"\n{details}"
            print(msg)
            if on_phase_callback:
                on_phase_callback(msg)

        log_phase("Phase -1: 确定故事内核...")
        nucleus = self.story_nucleus.generate_nucleus(topic, character_config)
        log_phase(f"   内核: {nucleus['pattern_name']}")
        log_phase(f"   分享欲: {nucleus['sharing_urge']['description']}")
        log_phase(f"   反常点: {nucleus['abnormality']['description']}")
        log_phase(f"   开场意图: {nucleus['sharing_urge']['opening']}")
        nucleus_prompt = self._build_nucleus_prompt(nucleus)

        log_phase("Phase 0: 选择触发方式...")
        trigger = self.trigger_bank.sample(character_config or {}, language, context=None)
        log_phase(f"   触发类型: {trigger['type']}")
        log_phase(f"   开场: {trigger['filled'][:50]}...")

        log_phase("Phase 1: 建立沉浸状态...")
        immersion = self._build_immersion(name, persona, topic, trigger)
        log_phase(f"   沉浸: {immersion[:100]}...")

        primary_emotion = self._infer_emotion(topic, background)
        emotion_config = self.emotion_mixer.mix(primary_emotion, language=language)
        emotion_msg = (
            f"情绪配置: {emotion_config.primary}"
            + (f" + {emotion_config.secondary}" if emotion_config.secondary else "")
            + (f" (masked as {emotion_config.mask})" if emotion_config.mask else "")
        )
        log_phase(emotion_msg)

        fewshot = ""
        if self.example_sampler:
            clips = self.example_sampler.sample_diverse(n=3, language=language)
            if clips:
                fewshot = "## 真实主播风格参考\n\n" + self.example_sampler.format_as_fewshot(clips)

        min_units = 8
        max_units = 10
        if character_config:
            min_units = int(character_config.get("min_units", min_units))
            max_units = int(character_config.get("max_units", max_units))
            if max_units < min_units:
                max_units = min_units

        log_phase("Phase 2: 生成初版剧本...")
        system = self.SYSTEM_PROMPT_V4 + "\n\n" + fewshot

        # Language instructions for LLM
        language_instructions = {
            "zh": "- 所有对话内容必须用中文（简体）生成\n- 使用自然口语化的中文表达",
            "en": "- Generate ALL dialogue content in English\n- Use natural, casual English expressions",
            "ja": "- すべての対話内容を日本語で生成\n- 自然な口語的な日本語表現を使用",
        }

        user_prompt = f"""{nucleus_prompt}

## 当前状态
{immersion}

## 触发开场（必须使用这个开场，并体现分享欲）
{trigger['filled']}

## 角色信息
- 名字: {name}
- 人设: {persona}
- 背景: {background}
- 话题: {topic}

## 语言要求（重要）
{language_instructions.get(language, language_instructions['zh'])}

## 情绪配置
- 主情绪: {emotion_config.primary}
- 副情绪: {emotion_config.secondary or '无'}
- 情绪标记可用: {emotion_config.markers}

## 生成要求（以本次为准，覆盖系统数量提示）
- {min_units}-{max_units}个单元，每个80-120字
- 开场必须用上面的触发
- 开场必须体现"为什么现在要说"
- 至少1段严重跑题（50字+）
- 必须有反常点（行为/反应/逻辑/身份/结果/认知落差）
- 至少一处内心独白 + 一处身体记忆 + 一处笨拙失控
- 不要升华结尾
- 只输出JSON数组
"""

        response = self.llm.call(user_prompt, system=system, max_tokens=8000)
        lines = self._parse_response(response, trigger["type"])
        lines = self._ensure_min_units(lines, trigger["type"], min_units, max_units, user_prompt, system)

        log_phase("Phase 3: 结构破坏...")
        lines_dict = [self._line_to_dict(line) for line in lines]
        broken_lines_dict = self.structure_breaker.break_structure(
            lines_dict, topic, language, character_config
        )
        if len(broken_lines_dict) < min_units:
            log_phase("结构破坏后单元数过少，保留原始结构。")
        else:
            lines_dict = broken_lines_dict

        result = [self._dict_to_line(d) for d in lines_dict]

        log_phase(f"生成完成，共 {len(result)} 个单元")
        return result

    def _build_immersion(self, name: str, persona: str, topic: str, trigger: dict) -> str:
        """构建沉浸状态描述"""
        prompt = f"""你是{name}，{persona}。

你正在直播。刚刚{self._trigger_to_description(trigger)}，让你想起了"{topic}"。

用50-80字描述你现在的状态（第一人称）：
- 是什么具体触发了这个回忆？
- 你现在什么心情？
- 你打算怎么开口？

不要写剧本，只描述状态。"""

        return self.llm.call(prompt, max_tokens=200)

    def _build_nucleus_prompt(self, nucleus: dict) -> str:
        """构建故事内核提示"""
        structure_lines = []
        for key, text in nucleus.get("structure", []):
            structure_lines.append(f"- {key}: {text}")
        structure_text = "\n".join(structure_lines)

        prompts = nucleus.get("key_prompts", [])
        prompt_text = "\n".join([f"- {p}" for p in prompts])

        return self.NUCLEUS_PROMPT_TEMPLATE.format(
            sharing_urge_description=nucleus["sharing_urge"]["description"],
            opening_template=nucleus["sharing_urge"]["opening"],
            abnormality_description=nucleus["abnormality"]["description"],
            structure=structure_text,
            key_prompts=prompt_text,
        )

    def _trigger_to_description(self, trigger: dict) -> str:
        """将触发转换为描述"""
        type_desc = {
            "sensory": "吃到/闻到/看到了什么",
            "environment": "被环境打断了",
            "body_state": "感受到身体的某种状态",
            "thought_drift": "脑子里突然冒出一个念头",
            "danmaku": "看到了一条弹幕",
            "unconscious": "做了一个无意识的动作",
        }
        return type_desc.get(trigger["type"], "发生了一件小事")

    def _infer_emotion(self, topic: str, background: str) -> str:
        """根据话题推断主要情绪"""
        topic_lower = topic.lower() + background.lower()

        if any(w in topic_lower for w in ["尴尬", "丢人", "embarrass", "shame"]):
            return "embarrassed"
        if any(w in topic_lower for w in ["感动", "温暖", "touch", "warm"]):
            return "touched"
        if any(w in topic_lower for w in ["生气", "愤怒", "angry", "mad"]):
            return "angry"
        if any(w in topic_lower for w in ["难过", "sad", "miss"]):
            return "sad"
        if any(w in topic_lower for w in ["开心", "搞笑", "happy", "funny"]):
            return "happy"
        if any(w in topic_lower for w in ["紧张", "害怕", "nervous", "scared"]):
            return "anxious"
        if any(w in topic_lower for w in ["以前", "回忆", "那时候", "remember"]):
            return "nostalgic"

        return "nostalgic"

    def _parse_response(self, response: str, trigger_type: str) -> List[ScriptLineV4]:
        """解析LLM响应"""
        json_match = re.search(r"\[[\s\S]*\]", response)
        if not json_match:
            print(f"⚠️ 无法解析JSON: {response[:200]}...")
            return []

        try:
            data = json.loads(json_match.group())
            lines = []

            for i, item in enumerate(data):
                text = item.get("text", "")
                stage = item.get("stage", "Build-up")

                # 生成 PerformerCue
                cue = self._generate_cue_for_line(text, stage, i)

                line = ScriptLineV4(
                    id=item.get("id", f"line_{i}"),
                    text=text,
                    stage=stage,
                    interruption_cost=item.get("cost", 0.5),
                    key_info=item.get("key_info", []),
                    disfluencies=item.get("disfluencies", []),
                    emotion_break=item.get("emotion_break"),
                    trigger_type=trigger_type if i == 0 else "continuation",
                    cue=cue,
                )
                lines.append(line)

            return lines

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析错误: {e}")
            return []

    def _generate_cue_for_line(self, text: str, stage: str, line_idx: int) -> PerformerCue:
        """
        为单行台词生成表演标注

        Args:
            text: 台词文本
            stage: 叙事阶段
            line_idx: 台词索引

        Returns:
            PerformerCue 实例
        """
        # 1. 推断表情
        emotion_cue = infer_emotion_from_text(text, stage)

        # 2. 选择合适的动作
        gesture_cue = None
        gesture_preset = get_gesture_for_stage(stage, emotion_cue.key.value)
        if gesture_preset:
            gesture_cue = GestureCue(
                clip=gesture_preset.name,
                weight=gesture_preset.weight,
                duration=gesture_preset.duration,
                loop=gesture_preset.loop,
            )

        # 3. 视线目标 - 根据阶段调整
        look_target = LookTarget.CAMERA
        if stage == "Hook":
            look_target = LookTarget.CAMERA
        elif "弹幕" in text or "评论" in text or "有人问" in text:
            look_target = LookTarget.CHAT
        elif "..." in text or "…" in text:
            look_target = LookTarget.DOWN  # 思考时看下方

        look_cue = LookCue(
            target=look_target,
            strength=0.8 if stage in ["Hook", "Climax"] else 0.6,
        )

        # 4. 眨眼模式
        blink_mode = BlinkMode.AUTO
        if "！" in text or "!!" in text:
            blink_mode = BlinkMode.HOLD  # 激动时保持睁眼
        blink_cue = BlinkCue(mode=blink_mode)

        # 5. 口型 - 预留，实际由音频驱动
        lipsync_cue = LipsyncCue(enabled=True)

        # 6. 节拍/暂停
        beat = None
        pause = None
        if stage == "Climax":
            beat = 0.5  # 高潮前的节拍点
        if "..." in text or "…" in text:
            pause = 0.3  # 省略号处暂停

        return PerformerCue(
            emotion=emotion_cue,
            gesture=gesture_cue,
            look=look_cue,
            blink=blink_cue,
            lipsync=lipsync_cue,
            beat=beat,
            pause=pause,
        )

    def _ensure_min_units(
        self,
        lines: List[ScriptLineV4],
        trigger_type: str,
        min_units: int,
        max_units: int,
        original_prompt: str,
        system: str,
    ) -> List[ScriptLineV4]:
        """确保最小单元数，必要时触发补全。"""
        if len(lines) >= min_units:
            return lines

        # 有 LLM 时尝试补全
        retry_prompt = f"""你上次输出的 JSON 只有 {len(lines)} 条，请补齐到 {min_units}-{max_units} 条。
只输出 JSON 数组，不要其他内容。

原始要求如下：
{original_prompt}
"""
        response = self.llm.call(retry_prompt, system=system, max_tokens=8000)
        retry_lines = self._parse_response(response, trigger_type)
        if len(retry_lines) >= min_units:
            return retry_lines
        raise ValueError(f"剧本单元数不足: {len(retry_lines)} / {min_units}")

    def _line_to_dict(self, line: ScriptLineV4) -> dict:
        """ScriptLineV4 转 dict"""
        result = {
            "id": line.id,
            "text": line.text,
            "stage": line.stage,
            "cost": line.interruption_cost,
            "key_info": line.key_info,
            "disfluencies": line.disfluencies,
            "emotion_break": line.emotion_break,
            "trigger_type": line.trigger_type,
            "is_digression": line.is_digression,
        }
        if line.cue:
            result["cue"] = line.cue.to_dict()
        return result

    def _dict_to_line(self, d: dict) -> ScriptLineV4:
        """dict 转 ScriptLineV4"""
        # 解析 cue
        cue = None
        if "cue" in d and d["cue"]:
            cue = PerformerCue.from_dict(d["cue"])

        return ScriptLineV4(
            id=d.get("id", ""),
            text=d.get("text", ""),
            stage=d.get("stage", ""),
            interruption_cost=d.get("cost", 0.5),
            key_info=d.get("key_info", []),
            disfluencies=d.get("disfluencies", []),
            emotion_break=d.get("emotion_break"),
            trigger_type=d.get("trigger_type", ""),
            is_digression=d.get("is_digression", False),
            has_digression=d.get("has_digression", False),
            cue=cue,
        )


ScriptGeneratorV4 = ScriptGeneratorV4_1
