#!/usr/bin/env python3
"""
echuu - AI VTuber Performance Engine
=====================================
单Agent + 三阶段架构

用户输入: VTuber名称、设定、背景、直播主题
输出: 预置脚本 + 实时表演文本（含内心独白）

核心创新:
1. Interruption Cost - 动态决定是否回应弹幕
2. Inner Monologue可见 - 让观众看到AI的"思考过程"  
3. 数据驱动 - 从真实主播切片学习行为模式
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict, Counter
from openai import OpenAI

# ============================================================
# Part 1: 数据结构
# ============================================================

class AttentionFocus(str, Enum):
    SELF = "self"           # 讲自己的事
    AUDIENCE = "audience"   # 和观众互动
    CONTENT = "content"     # 讲内容/知识
    SPECIFIC = "specific"   # 对特定人/物
    META = "meta"           # 关于直播本身


class SpeechAct(str, Enum):
    NARRATE = "narrate"     # 叙述故事
    OPINE = "opine"         # 发表观点
    RESPOND = "respond"     # 回应弹幕
    ELICIT = "elicit"       # 引导互动
    PIVOT = "pivot"         # 转场


class Decision(str, Enum):
    CONTINUE = "continue"   # 继续剧本
    RESPOND = "respond"     # 回应弹幕
    IMPROVISE = "improvise" # 跑题即兴
    SILENCE = "silence"     # 沉默/思考
    REACT = "react"         # 非语言反应


@dataclass
class NarrativeNode:
    """剧本中的一个叙事节点"""
    stage: str
    goal: str
    target_attention: str
    target_speech_act: str
    duration_sec: int
    interruption_cost: float
    content_hint: str = ""
    
    def get_current_cost(self, elapsed_ratio: float) -> float:
        """随着节点进度推进，cost会降低"""
        if elapsed_ratio > 0.8:
            return self.interruption_cost * 0.5
        elif elapsed_ratio > 0.5:
            return self.interruption_cost * 0.8
        return self.interruption_cost


@dataclass
class Danmaku:
    """弹幕"""
    text: str
    urgency: float = 0.3
    is_sc: bool = False
    
    @classmethod
    def from_text(cls, text: str) -> "Danmaku":
        urgency = 0.3
        is_sc = False
        if any(kw in text for kw in ["SC", "¥", "$", "打赏", "礼物"]):
            urgency = 0.9
            is_sc = True
        elif "?" in text or "？" in text:
            urgency = 0.5
        elif any(kw in text for kw in ["生日", "第一次", "求", "帮", "怎么办"]):
            urgency = 0.6
        return cls(text=text, urgency=urgency, is_sc=is_sc)


@dataclass
class PerformanceState:
    """表演状态"""
    name: str
    persona: str
    background: str
    topic: str
    
    script: List[NarrativeNode] = field(default_factory=list)
    current_node_idx: int = 0
    node_elapsed_sec: float = 0.0
    
    danmaku_queue: List[Danmaku] = field(default_factory=list)
    ignored_count: int = 0
    
    performance_log: List[Dict] = field(default_factory=list)
    total_elapsed_sec: float = 0.0
    
    catchphrases: List[str] = field(default_factory=list)
    example_hooks: List[str] = field(default_factory=list)
    example_punchlines: List[str] = field(default_factory=list)


# ============================================================
# Part 2: Pattern Analyzer - 从数据学习
# ============================================================

class PatternAnalyzer:
    """从标注数据中提取模式"""
    
    def __init__(self, annotated_clips: List[Dict]):
        self.clips = annotated_clips
        self.all_segments = []
        for clip in annotated_clips:
            self.all_segments.extend(clip.get("segments", []))
    
    def compute_attention_transitions(self) -> Dict[str, Dict[str, float]]:
        """计算attention转移概率"""
        trans = defaultdict(lambda: defaultdict(int))
        for clip in self.clips:
            segs = clip.get("segments", [])
            for i in range(len(segs) - 1):
                f = segs[i].get("attention_focus", "self")
                t = segs[i+1].get("attention_focus", "self")
                trans[f][t] += 1
        
        prob = {}
        for f, tos in trans.items():
            total = sum(tos.values())
            prob[f] = {t: c/total for t, c in tos.items()}
        return prob
    
    def infer_baseline_costs(self) -> Dict[str, float]:
        """推断不同attention下被打断的代价"""
        focus_stats = defaultdict(lambda: {"total": 0, "ignored": 0})
        
        for seg in self.all_segments:
            focus = seg.get("attention_focus", "self")
            trigger = seg.get("trigger", "self")
            act = seg.get("speech_act", "narrate")
            
            if trigger == "danmaku":
                focus_stats[focus]["total"] += 1
                if act != "respond":
                    focus_stats[focus]["ignored"] += 1
        
        costs = {}
        for focus, stats in focus_stats.items():
            if stats["total"] > 0:
                costs[focus] = stats["ignored"] / stats["total"]
            else:
                costs[focus] = 0.5
        return costs
    
    def extract_skeletons(self) -> List[Tuple[str, int]]:
        """提取叙事骨架"""
        skeletons = [c.get("skeleton", "") for c in self.clips if c.get("skeleton")]
        return Counter(skeletons).most_common(10)
    
    def extract_catchphrases(self, language: str = None) -> List[Tuple[str, int]]:
        """提取口癖"""
        cps = []
        for c in self.clips:
            if language and c.get("language") != language:
                continue
            cps.extend(c.get("catchphrases", []))
        return Counter(cps).most_common(20)
    
    def extract_hooks(self, language: str = None) -> List[str]:
        """提取开场示例"""
        hooks = []
        for c in self.clips:
            if language and c.get("language") != language:
                continue
            segs = c.get("segments", [])
            if segs:
                hooks.append(segs[0].get("text", "")[:100])
        return hooks[:10]
    
    def extract_punchlines(self, language: str = None) -> List[str]:
        """提取收尾示例"""
        punches = []
        for c in self.clips:
            if language and c.get("language") != language:
                continue
            segs = c.get("segments", [])
            if segs:
                punches.append(segs[-1].get("text", "")[:100])
        return punches[:10]
    
    def get_report(self) -> str:
        lines = [
            "=" * 50,
            "📊 Pattern Analysis Report",
            "=" * 50,
            f"Total clips: {len(self.clips)}, Total segments: {len(self.all_segments)}",
        ]
        
        lines.append("\n--- Attention Transitions ---")
        for f, tos in self.compute_attention_transitions().items():
            top = sorted(tos.items(), key=lambda x: -x[1])[:3]
            lines.append(f"  {f} → " + ", ".join(f"{t}:{p:.0%}" for t, p in top))
        
        lines.append("\n--- Inferred Interruption Costs ---")
        for focus, cost in self.infer_baseline_costs().items():
            lines.append(f"  {focus}: {cost:.2f}")
        
        lines.append("\n--- Top Catchphrases ---")
        cps = self.extract_catchphrases()[:10]
        lines.append("  " + ", ".join(f'"{c}"({n})' for c, n in cps))
        
        return "\n".join(lines)


# ============================================================
# Part 3: LLM Client
# ============================================================

class LLMClient:
    """LLM调用封装"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.anthropic.com/v1/"
            )
        else:
            self.client = None
    
    def call(self, prompt: str, system: str = None, max_tokens: int = 2000) -> str:
        """调用LLM"""
        if not self.client:
            return self._mock_response(prompt)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """无API时的mock响应"""
        if "生成剧本" in prompt or "script" in prompt.lower():
            return """[
{"stage": "Hook", "goal": "用一个引人注目的话题吸引注意", "attention": "audience", "speech_act": "elicit", "duration": 20, "cost": 0.3, "hint": "提出一个观众可能共鸣的问题"},
{"stage": "Build-up", "goal": "铺垫背景和情绪", "attention": "self", "speech_act": "narrate", "duration": 40, "cost": 0.6, "hint": "分享相关的个人经历"},
{"stage": "Climax", "goal": "讲述最关键的部分", "attention": "self", "speech_act": "narrate", "duration": 40, "cost": 0.9, "hint": "情感爆发点"},
{"stage": "Resolution", "goal": "总结和升华", "attention": "audience", "speech_act": "opine", "duration": 20, "cost": 0.4, "hint": "给观众一个takeaway"}
]"""
        elif "cognitive" in prompt.lower() or "决策" in prompt:
            return """{
"inner_monologue": "这段故事对我很重要，想先讲完...",
"decision": "continue",
"speech": "说到这个，我想起了...",
"emotion": "reflective"
}"""
        else:
            return "Mock response"


# ============================================================
# Part 4: Script Generator - 剧本生成
# ============================================================

class ScriptGenerator:
    """剧本骨架生成器"""
    
    SYSTEM_PROMPT = """你是一个专业的VTuber剧本编剧。你需要根据角色设定和直播主题，设计一个2分钟的表演剧本骨架。

你熟悉真人主播的叙事模式：
- Hook: 用问题/悬念/共鸣点开场
- Build-up: 铺垫背景、积累情绪
- Climax: 情感爆发点、关键信息
- Resolution: 总结升华、和观众连接

你需要考虑interruption_cost（被弹幕打断的代价）：
- 0.0-0.3: 可以随时打断（闲聊、开场）
- 0.4-0.6: 最好不打断但可以（铺垫阶段）
- 0.7-0.9: 尽量不打断（高潮阶段）
- 0.9+: 绝对不能打断（情感爆发）"""

    def __init__(self, llm: LLMClient, analyzer: PatternAnalyzer = None):
        self.llm = llm
        self.analyzer = analyzer
        self.baseline_costs = analyzer.infer_baseline_costs() if analyzer else {}
    
    def generate(self, name: str, persona: str, background: str, 
                 topic: str, language: str = "zh") -> List[NarrativeNode]:
        """生成剧本骨架"""
        
        # 获取参考数据
        example_skeletons = ""
        example_hooks = ""
        example_punchlines = ""
        catchphrases = ""
        
        if self.analyzer:
            skels = self.analyzer.extract_skeletons()[:3]
            example_skeletons = "\n".join(f"- {s}" for s, _ in skels)
            
            hooks = self.analyzer.extract_hooks(language)[:3]
            example_hooks = "\n".join(f'- "{h}"' for h in hooks)
            
            punches = self.analyzer.extract_punchlines(language)[:3]
            example_punchlines = "\n".join(f'- "{p}"' for p in punches)
            
            cps = self.analyzer.extract_catchphrases(language)[:5]
            catchphrases = ", ".join(f'"{c}"' for c, _ in cps)
        
        prompt = f"""请为以下VTuber设计一个2分钟的直播剧本骨架：

## 角色信息
- 名字: {name}
- 人设: {persona}
- 背景: {background}
- 今日话题: {topic}

## 参考：真人主播的叙事骨架
{example_skeletons or "（无参考数据）"}

## 参考：开场Hook示例
{example_hooks or "（无参考数据）"}

## 参考：收尾Punchline示例  
{example_punchlines or "（无参考数据）"}

## 可选口癖
{catchphrases or "（无参考数据）"}

## 输出要求
输出一个JSON数组，每个元素代表一个叙事节点：
```json
[
  {{
    "stage": "Hook/Build-up/Climax/Resolution/...",
    "goal": "这个阶段要达成的目标（20字内）",
    "attention": "self/audience/content/specific",
    "speech_act": "narrate/opine/respond/elicit/pivot",
    "duration": 秒数,
    "cost": 0.0-1.0的interruption_cost,
    "hint": "内容提示（可选）"
  }}
]
```

请设计4-6个节点，总时长约120秒。直接输出JSON，不要其他内容。"""

        response = self.llm.call(prompt, system=self.SYSTEM_PROMPT)
        
        # 解析响应
        try:
            # 提取JSON部分
            if "```" in response:
                json_str = response.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            else:
                json_str = response
            
            nodes_data = json.loads(json_str.strip())
            
            nodes = []
            for n in nodes_data:
                node = NarrativeNode(
                    stage=n.get("stage", "Unknown"),
                    goal=n.get("goal", ""),
                    target_attention=n.get("attention", "self"),
                    target_speech_act=n.get("speech_act", "narrate"),
                    duration_sec=n.get("duration", 30),
                    interruption_cost=n.get("cost", 0.5),
                    content_hint=n.get("hint", "")
                )
                nodes.append(node)
            return nodes
            
        except Exception as e:
            print(f"Parse error: {e}")
            return self._fallback_script(topic)
    
    def _fallback_script(self, topic: str) -> List[NarrativeNode]:
        """解析失败时的后备剧本"""
        return [
            NarrativeNode("Hook", f"引出{topic}", "audience", "elicit", 20, 0.3),
            NarrativeNode("Build-up", "铺垫背景", "self", "narrate", 40, 0.6),
            NarrativeNode("Climax", "核心内容", "self", "narrate", 40, 0.9),
            NarrativeNode("Resolution", "总结升华", "audience", "opine", 20, 0.4),
        ]


# ============================================================
# Part 5: Cognitive Performer - 实时表演
# ============================================================

class CognitivePerformer:
    """认知表演者 - 实时决策和生成"""
    
    SYSTEM_PROMPT = """你是一个VTuber的"内心"。你需要在每个时刻：
1. 感知当前状态（剧本进度、弹幕、时间）
2. 做出决策（继续剧本/回应弹幕/即兴/沉默）
3. 输出内心独白（这会显示给观众，是killer feature）
4. 生成台词

关键：内心独白要展示你的"思考过程"，让观众感受到AI的agency。
- 不是假装像人，而是让观众看到你在"思考"和"选择"
- "选择不回应"也是一种表达
- 内心独白要简短、真实、有personality"""

    def __init__(self, llm: LLMClient, analyzer: PatternAnalyzer = None):
        self.llm = llm
        self.analyzer = analyzer
    
    def step(self, state: PerformanceState, new_danmaku: List[Danmaku] = None) -> Dict:
        """执行一次认知循环"""
        
        if new_danmaku:
            state.danmaku_queue.extend(new_danmaku)
        
        # 检查是否结束
        if state.current_node_idx >= len(state.script):
            return self._generate_ending(state)
        
        current_node = state.script[state.current_node_idx]
        elapsed_ratio = state.node_elapsed_sec / current_node.duration_sec if current_node.duration_sec > 0 else 1.0
        current_cost = current_node.get_current_cost(elapsed_ratio)
        
        # 评估弹幕
        max_urgency = 0.0
        most_urgent = None
        for d in state.danmaku_queue:
            if d.urgency > max_urgency:
                max_urgency = d.urgency
                most_urgent = d
        
        # 构建prompt
        recent_danmaku = [d.text for d in state.danmaku_queue[-5:]]
        
        prompt = f"""## 当前状态

### 角色
名字: {state.name}
人设: {state.persona}

### 剧本进度
当前阶段: {current_node.stage}
阶段目标: {current_node.goal}
阶段进度: {elapsed_ratio:.0%}
内容提示: {current_node.content_hint}

### 叙事代价
当前cost: {current_cost:.2f} (0=随意打断, 1=绝对不能打断)

### 弹幕情况
最近弹幕: {recent_danmaku or "（无）"}
最高紧急度: {max_urgency:.2f}
连续忽略数: {state.ignored_count}

### 决策参考
urgency - cost = {max_urgency - current_cost:.2f}
正数倾向回应，负数倾向继续
连续忽略3条以上应考虑补救

### 口癖参考
{state.catchphrases[:3] if state.catchphrases else "（无）"}

## 输出要求
输出JSON：
```json
{{
  "inner_monologue": "内心独白（20字内，显示给观众）",
  "decision": "continue/respond/improvise/silence",
  "speech": "台词（如果要说话）",
  "emotion": "情绪状态"
}}
```

直接输出JSON。"""

        response = self.llm.call(prompt, system=self.SYSTEM_PROMPT, max_tokens=500)
        
        # 解析
        try:
            if "```" in response:
                json_str = response.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            else:
                json_str = response
            result = json.loads(json_str.strip())
        except:
            result = {
                "inner_monologue": f"继续讲{current_node.stage}...",
                "decision": "continue",
                "speech": f"说到{state.topic}...",
                "emotion": "neutral"
            }
        
        # 更新状态
        decision = result.get("decision", "continue")
        step_duration = 10
        state.node_elapsed_sec += step_duration
        state.total_elapsed_sec += step_duration
        
        if state.node_elapsed_sec >= current_node.duration_sec:
            state.current_node_idx += 1
            state.node_elapsed_sec = 0
        
        if decision == "respond" and most_urgent:
            state.danmaku_queue = [d for d in state.danmaku_queue if d != most_urgent]
            state.ignored_count = 0
            result["target_danmaku"] = most_urgent.text
        elif decision == "continue" and state.danmaku_queue:
            state.ignored_count += 1
        
        result["node"] = current_node.stage
        result["time"] = f"{state.total_elapsed_sec:.0f}s"
        result["cost"] = current_cost
        result["urgency"] = max_urgency
        
        return result
    
    def _generate_ending(self, state: PerformanceState) -> Dict:
        return {
            "inner_monologue": "该收尾了~",
            "decision": "continue",
            "speech": f"好啦，今天关于{state.topic}就聊到这里，下次见！",
            "emotion": "satisfied",
            "node": "END",
            "time": f"{state.total_elapsed_sec:.0f}s"
        }


# ============================================================
# Part 6: Main Engine
# ============================================================

class EchuuEngine:
    """echuu核心引擎"""
    
    def __init__(self, data_path: str = None, api_key: str = None):
        # 加载数据
        self.clips = []
        if data_path and os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                self.clips = json.load(f)
        
        # 初始化组件
        self.analyzer = PatternAnalyzer(self.clips) if self.clips else None
        self.llm = LLMClient(api_key)
        self.script_gen = ScriptGenerator(self.llm, self.analyzer)
        self.performer = CognitivePerformer(self.llm, self.analyzer)
    
    def create_performance(self, name: str, persona: str, background: str,
                          topic: str, language: str = "zh") -> PerformanceState:
        """创建表演"""
        
        # 生成剧本
        print(f"\n🎬 正在生成剧本...")
        script = self.script_gen.generate(name, persona, background, topic, language)
        
        # 提取参考数据
        catchphrases = []
        hooks = []
        punchlines = []
        if self.analyzer:
            catchphrases = [cp for cp, _ in self.analyzer.extract_catchphrases(language)[:5]]
            hooks = self.analyzer.extract_hooks(language)[:3]
            punchlines = self.analyzer.extract_punchlines(language)[:3]
        
        return PerformanceState(
            name=name,
            persona=persona,
            background=background,
            topic=topic,
            script=script,
            catchphrases=catchphrases,
            example_hooks=hooks,
            example_punchlines=punchlines
        )
    
    def run(self, state: PerformanceState, danmaku_sim: List[Dict] = None,
            max_steps: int = 12) -> List[Dict]:
        """运行表演"""
        
        results = []
        danmaku_by_step = defaultdict(list)
        if danmaku_sim:
            for d in danmaku_sim:
                step = d.get("step", 0)
                danmaku_by_step[step].append(Danmaku.from_text(d.get("text", "")))
        
        print(f"\n{'='*60}")
        print(f"🎭 {state.name} - {state.topic}")
        print(f"{'='*60}")
        
        print(f"\n📋 剧本骨架:")
        for i, node in enumerate(state.script):
            print(f"  [{i+1}] {node.stage} (cost={node.interruption_cost:.2f})")
            print(f"      → {node.goal}")
        
        print(f"\n🎬 开始表演...\n")
        
        for step in range(max_steps):
            new_danmaku = danmaku_by_step.get(step, [])
            result = self.performer.step(state, new_danmaku)
            results.append(result)
            
            # 打印
            print(f"[{result.get('time', '?')}] {result.get('node', '?')}")
            print(f"  💭 {result.get('inner_monologue', '')}")
            decision = result.get('decision', 'continue').upper()
            speech = result.get('speech', '(沉默)')
            print(f"  📢 {decision}: {speech}")
            if result.get('target_danmaku'):
                print(f"  💬 回应: {result['target_danmaku']}")
            print()
            
            if result.get('node') == "END":
                break
        
        print(f"{'='*60}")
        print(f"✅ 表演结束！总时长: {state.total_elapsed_sec:.0f}秒")
        print(f"{'='*60}")
        
        return results
    
    def export_script(self, state: PerformanceState) -> Dict:
        """导出剧本为JSON"""
        return {
            "character": {
                "name": state.name,
                "persona": state.persona,
                "background": state.background
            },
            "topic": state.topic,
            "script": [
                {
                    "stage": n.stage,
                    "goal": n.goal,
                    "attention": n.target_attention,
                    "speech_act": n.target_speech_act,
                    "duration_sec": n.duration_sec,
                    "interruption_cost": n.interruption_cost,
                    "hint": n.content_hint
                }
                for n in state.script
            ],
            "catchphrases": state.catchphrases
        }


# ============================================================
# Part 7: Demo
# ============================================================

def demo():
    """演示"""
    
    # 初始化
    data_path = "/mnt/user-data/uploads/annotated_clips.json"
    if not os.path.exists(data_path):
        data_path = "annotated_clips.json"
    
    engine = EchuuEngine(data_path if os.path.exists(data_path) else None)
    
    # 打印分析报告
    if engine.analyzer:
        print(engine.analyzer.get_report())
    
    # 测试用例
    test = {
        "name": "六螺",
        "persona": "25岁主播，活泼自嘲，喜欢分享生活经历，口癖：我觉得、对吧",
        "background": "做过很多工作，现在是全职主播，经常和观众聊人生",
        "topic": "留学时偷吃室友腰果的故事",
        "danmaku": [
            {"step": 1, "text": "哈哈哈"},
            {"step": 3, "text": "我也有类似经历"},
            {"step": 5, "text": "[SC ¥50] 后来室友生气了吗"},
            {"step": 7, "text": "笑死"},
            {"step": 9, "text": "太真实了"},
        ]
    }
    
    # 创建表演
    state = engine.create_performance(
        name=test["name"],
        persona=test["persona"],
        background=test["background"],
        topic=test["topic"],
        language="zh"
    )
    
    # 导出剧本
    script_json = engine.export_script(state)
    print("\n📄 导出的剧本JSON:")
    print(json.dumps(script_json, ensure_ascii=False, indent=2))
    
    # 运行表演
    results = engine.run(state, test["danmaku"], max_steps=12)
    
    # 导出表演日志
    print("\n📄 表演日志:")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
