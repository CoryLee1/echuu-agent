"""
echuu Live Engine - 集成 Claude LLM + 通义千问 TTS 的实时直播引擎

核心功能:
1. Claude LLM 生成直播台词和内心独白
2. CosyVoice TTS 实时语音合成
3. 支持弹幕互动和打断机制
"""

import os
import json
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================
# LLM Client
# ============================================

class ClaudeLLMClient:
    """Claude LLM 客户端"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("DEFAULT_MODEL", "claude-3-haiku-20240307")
        self.client = None
        
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                print(f"✅ Claude LLM 初始化: model={self.model}")
            except ImportError:
                print("⚠️ anthropic 未安装，请运行: pip install anthropic")
        else:
            print("⚠️ 未设置 ANTHROPIC_API_KEY，LLM 将使用 Mock 模式")
    
    def call(self, prompt: str, system: str = None, max_tokens: int = 1000) -> str:
        """调用 Claude LLM"""
        if self.client:
            try:
                messages = [{"role": "user", "content": prompt}]
                
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": messages
                }
                if system:
                    kwargs["system"] = system
                
                response = self.client.messages.create(**kwargs)
                return response.content[0].text
            except Exception as e:
                print(f"[LLM] 调用错误: {e}")
        
        return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Mock 响应"""
        import random
        
        monologues = ["让我想想...", "有意思...", "好，继续说...", "嗯..."]
        speeches = ["说起这个事儿啊...", "你们知道吗...", "我跟你们讲..."]
        
        return json.dumps({
            "inner_monologue": random.choice(monologues),
            "decision": "continue",
            "speech": random.choice(speeches),
            "emotion": "neutral"
        }, ensure_ascii=False)


# ============================================
# TTS Client (简化版)
# ============================================

class TTSClient:
    """TTS 客户端封装"""
    
    def __init__(self):
        self.tts = None
        self.enabled = False
        
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if api_key:
            try:
                from workflow.backend.tts_client import CosyVoiceTTS
                self.tts = CosyVoiceTTS()
                self.enabled = True
                print("✅ TTS 已启用")
            except Exception as e:
                print(f"⚠️ TTS 初始化失败: {e}")
        else:
            print("⚠️ 未设置 DASHSCOPE_API_KEY，TTS 已禁用")
    
    def speak(self, text: str, save_path: str = None) -> Optional[bytes]:
        """合成语音"""
        if not self.enabled or not self.tts:
            print(f"[TTS] (禁用) {text[:50]}...")
            return None
        
        try:
            return self.tts.synthesize(text, save_path)
        except Exception as e:
            print(f"[TTS] 合成错误: {e}")
            return None
    
    def speak_streaming(self, texts: List[str], save_path: str = None) -> Optional[bytes]:
        """流式合成语音"""
        if not self.enabled or not self.tts:
            return None
        
        try:
            return self.tts.synthesize_streaming(texts, save_path)
        except Exception as e:
            print(f"[TTS] 流式合成错误: {e}")
            return None


# ============================================
# 数据结构
# ============================================

@dataclass
class NarrativeNode:
    """剧本节点"""
    stage: str
    goal: str
    target_attention: str
    target_speech_act: str
    duration_sec: int
    interruption_cost: float
    content_hint: str = ""
    
    def get_current_cost(self, elapsed_ratio: float) -> float:
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
    timestamp: float = 0.0
    
    @classmethod
    def from_text(cls, text: str, timestamp: float = 0.0) -> "Danmaku":
        urgency = 0.3
        is_sc = False
        
        if any(kw in text for kw in ["SC", "¥", "$", "打赏", "礼物"]):
            urgency = 0.9
            is_sc = True
        elif "?" in text or "？" in text:
            urgency = 0.5
        elif any(kw in text for kw in ["生日", "第一次", "求", "帮"]):
            urgency = 0.6
        
        return cls(text=text, urgency=urgency, is_sc=is_sc, timestamp=timestamp)


@dataclass
class PerformanceOutput:
    """单次表演输出"""
    inner_monologue: str  # 内心独白 (可见)
    speech: str           # 台词
    emotion: str          # 情绪
    decision: str         # 决策 (continue/respond/silence)
    node: str             # 当前节点
    time_sec: float       # 时间点
    audio: Optional[bytes] = None  # 语音数据


# ============================================
# echuu Live Engine
# ============================================

class EchuuLiveEngine:
    """
    echuu 实时直播引擎
    
    集成:
    - Claude LLM: 生成台词和内心独白
    - CosyVoice TTS: 实时语音合成
    - Interruption Cost: 动态打断机制
    
    使用方法:
        engine = EchuuLiveEngine()
        
        # 创建表演
        engine.setup(
            name="六螺",
            persona="25岁主播，活泼自嘲",
            topic="留学时偷吃室友腰果的故事"
        )
        
        # 运行表演
        for output in engine.run():
            print(f"💭 {output.inner_monologue}")
            print(f"📢 {output.speech}")
            # 播放 output.audio
    """
    
    SYSTEM_PROMPT = """你是一个VTuber的"内心"。你需要在每个时刻：
1. 感知当前状态（剧本进度、弹幕、时间）
2. 做出决策（继续剧本/回应弹幕/即兴/沉默）
3. 输出内心独白（这会显示给观众）
4. 生成台词

关键：内心独白要展示你的"思考过程"，让观众感受到AI的agency。
- 不是假装像人，而是让观众看到你在"思考"和"选择"
- "选择不回应"也是一种表达
- 内心独白要简短、真实、有personality"""
    
    def __init__(self):
        self.llm = ClaudeLLMClient()
        self.tts = TTSClient()
        
        # 表演状态
        self.name = ""
        self.persona = ""
        self.background = ""
        self.topic = ""
        self.script: List[NarrativeNode] = []
        self.current_node_idx = 0
        self.node_elapsed_sec = 0.0
        self.total_elapsed_sec = 0.0
        self.danmaku_queue: List[Danmaku] = []
        self.ignored_count = 0
        
        # 配置
        self.step_duration = 10  # 每步时长（秒）
        self.enable_tts = True
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def setup(self, 
              name: str, 
              persona: str, 
              topic: str,
              background: str = "",
              script: List[Dict] = None):
        """设置表演参数"""
        self.name = name
        self.persona = persona
        self.background = background
        self.topic = topic
        self.current_node_idx = 0
        self.node_elapsed_sec = 0.0
        self.total_elapsed_sec = 0.0
        self.danmaku_queue = []
        self.ignored_count = 0
        
        # 生成或使用提供的剧本
        if script:
            self.script = [
                NarrativeNode(
                    stage=n.get("stage", "Unknown"),
                    goal=n.get("goal", ""),
                    target_attention=n.get("attention", "self"),
                    target_speech_act=n.get("speech_act", "narrate"),
                    duration_sec=n.get("duration", 30),
                    interruption_cost=n.get("cost", 0.5),
                    content_hint=n.get("hint", "")
                )
                for n in script
            ]
        else:
            self.script = self._generate_script()
        
        print(f"\n🎬 表演设置完成: {self.name} - {self.topic}")
        print(f"   剧本节点数: {len(self.script)}")
    
    def _generate_script(self) -> List[NarrativeNode]:
        """生成剧本骨架"""
        prompt = f"""请为以下VTuber设计一个2分钟的直播剧本骨架：

## 角色信息
- 名字: {self.name}
- 人设: {self.persona}
- 背景: {self.background}
- 今日话题: {self.topic}

## 输出要求
输出一个JSON数组，每个元素代表一个叙事节点，包含:
- stage: 阶段名称 (Hook/Build-up/Climax/Resolution)
- goal: 这个阶段的目标
- attention: 注意力焦点 (self/audience/specific)
- speech_act: 言语行为 (narrate/opine/respond/elicit)
- duration: 预计时长（秒）
- cost: 被打断的代价 (0.0-1.0)
- hint: 内容提示

请设计4-6个节点，总时长约120秒。只输出JSON数组。"""
        
        response = self.llm.call(prompt)
        
        try:
            # 提取 JSON
            if "```" in response:
                json_str = response.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            else:
                json_str = response
            
            nodes_data = json.loads(json_str.strip())
            
            return [
                NarrativeNode(
                    stage=n.get("stage", "Unknown"),
                    goal=n.get("goal", ""),
                    target_attention=n.get("attention", "self"),
                    target_speech_act=n.get("speech_act", "narrate"),
                    duration_sec=n.get("duration", 30),
                    interruption_cost=n.get("cost", 0.5),
                    content_hint=n.get("hint", "")
                )
                for n in nodes_data
            ]
        except Exception as e:
            print(f"[Script] 解析失败: {e}, 使用默认剧本")
            return self._default_script()
    
    def _default_script(self) -> List[NarrativeNode]:
        """默认剧本"""
        return [
            NarrativeNode("Hook", f"引出{self.topic}", "audience", "elicit", 20, 0.3, "用问题开场"),
            NarrativeNode("Build-up", "铺垫背景", "self", "narrate", 40, 0.6, "描述当时情况"),
            NarrativeNode("Climax", "核心内容", "self", "narrate", 40, 0.9, "关键转折"),
            NarrativeNode("Resolution", "总结升华", "audience", "opine", 20, 0.4, "分享感悟"),
        ]
    
    def add_danmaku(self, text: str):
        """添加弹幕"""
        danmaku = Danmaku.from_text(text, self.total_elapsed_sec)
        self.danmaku_queue.append(danmaku)
        print(f"[弹幕] {text} (urgency={danmaku.urgency:.1f})")
    
    def step(self) -> Optional[PerformanceOutput]:
        """执行一次认知循环"""
        # 检查是否结束
        if self.current_node_idx >= len(self.script):
            return self._generate_ending()
        
        current_node = self.script[self.current_node_idx]
        elapsed_ratio = self.node_elapsed_sec / current_node.duration_sec if current_node.duration_sec > 0 else 1.0
        current_cost = current_node.get_current_cost(elapsed_ratio)
        
        # 评估弹幕
        max_urgency = 0.0
        most_urgent = None
        for d in self.danmaku_queue:
            if d.urgency > max_urgency:
                max_urgency = d.urgency
                most_urgent = d
        
        # 构建 prompt
        recent_danmaku = [d.text for d in self.danmaku_queue[-5:]]
        
        prompt = f"""## 当前状态

### 角色
名字: {self.name}
人设: {self.persona}

### 剧本进度
当前阶段: {current_node.stage}
阶段目标: {current_node.goal}
阶段进度: {elapsed_ratio:.0%}
内容提示: {current_node.content_hint}

### 叙事代价
当前cost: {current_cost:.2f}

### 弹幕情况
最近弹幕: {recent_danmaku or "（无）"}
最高紧急度: {max_urgency:.2f}
连续忽略数: {self.ignored_count}

### 决策参考
urgency - cost = {max_urgency - current_cost:.2f}
正数倾向回应，负数倾向继续

## 输出
输出JSON: {{"inner_monologue": "...", "decision": "continue/respond", "speech": "...", "emotion": "..."}}
只输出JSON。"""
        
        response = self.llm.call(prompt, system=self.SYSTEM_PROMPT, max_tokens=500)
        
        # 解析响应
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
                "speech": f"说到{self.topic}...",
                "emotion": "neutral"
            }
        
        # 更新状态
        decision = result.get("decision", "continue")
        self.node_elapsed_sec += self.step_duration
        self.total_elapsed_sec += self.step_duration
        
        if self.node_elapsed_sec >= current_node.duration_sec:
            self.current_node_idx += 1
            self.node_elapsed_sec = 0
        
        if decision == "respond" and most_urgent:
            self.danmaku_queue = [d for d in self.danmaku_queue if d != most_urgent]
            self.ignored_count = 0
        elif decision == "continue" and self.danmaku_queue:
            self.ignored_count += 1
        
        # 生成语音
        speech = result.get("speech", "")
        audio = None
        if self.enable_tts and speech:
            audio_path = self.output_dir / f"step_{int(self.total_elapsed_sec)}.mp3"
            audio = self.tts.speak(speech, str(audio_path))
        
        return PerformanceOutput(
            inner_monologue=result.get("inner_monologue", ""),
            speech=speech,
            emotion=result.get("emotion", "neutral"),
            decision=decision,
            node=current_node.stage,
            time_sec=self.total_elapsed_sec,
            audio=audio
        )
    
    def _generate_ending(self) -> PerformanceOutput:
        """生成结尾"""
        speech = f"好啦，今天关于{self.topic}就聊到这里，下次见！"
        audio = None
        if self.enable_tts:
            audio_path = self.output_dir / f"ending.mp3"
            audio = self.tts.speak(speech, str(audio_path))
        
        return PerformanceOutput(
            inner_monologue="该收尾了~",
            speech=speech,
            emotion="satisfied",
            decision="end",
            node="END",
            time_sec=self.total_elapsed_sec,
            audio=audio
        )
    
    def run(self, max_steps: int = 12, danmaku_sim: List[Dict] = None):
        """
        运行完整表演
        
        Args:
            max_steps: 最大步数
            danmaku_sim: 模拟弹幕 [{"step": 1, "text": "..."}]
        
        Yields:
            PerformanceOutput
        """
        from collections import defaultdict
        
        danmaku_by_step = defaultdict(list)
        if danmaku_sim:
            for d in danmaku_sim:
                danmaku_by_step[d.get("step", 0)].append(d.get("text", ""))
        
        print(f"\n{'='*60}")
        print(f"🎭 {self.name} - {self.topic}")
        print(f"{'='*60}")
        
        print(f"\n📋 剧本:")
        for i, node in enumerate(self.script):
            cost_bar = "█" * int(node.interruption_cost * 5) + "░" * (5 - int(node.interruption_cost * 5))
            print(f"  [{i+1}] {node.stage} {cost_bar} cost={node.interruption_cost:.1f}")
        
        print(f"\n🎬 开始表演...\n")
        
        for step in range(max_steps):
            # 添加模拟弹幕
            for text in danmaku_by_step.get(step, []):
                self.add_danmaku(text)
            
            # 执行一步
            output = self.step()
            
            if output:
                # 打印输出
                dec_icon = "💬" if output.decision == "respond" else "📖" if output.decision == "continue" else "🎭"
                print(f"[{output.time_sec:.0f}s] {output.node} {dec_icon}")
                print(f"  💭 {output.inner_monologue}")
                print(f"  📢 {output.speech}")
                if output.audio:
                    print(f"  🔊 语音已生成")
                print()
                
                yield output
                
                if output.decision == "end":
                    break
        
        print(f"{'='*60}")
        print(f"✅ 表演结束！总时长: {self.total_elapsed_sec:.0f}秒")
        print(f"{'='*60}")


# ============================================
# 测试
# ============================================

if __name__ == "__main__":
    print("\n=== echuu Live Engine 测试 ===\n")
    
    engine = EchuuLiveEngine()
    
    # 设置表演
    engine.setup(
        name="六螺",
        persona="25岁主播，活泼自嘲，喜欢分享生活经历",
        topic="留学时偷吃室友腰果的故事",
        background="留学日本多年"
    )
    
    # 模拟弹幕
    danmaku = [
        {"step": 1, "text": "哈哈哈"},
        {"step": 3, "text": "我也有类似经历"},
        {"step": 5, "text": "[SC ¥50] 后来室友生气了吗"},
    ]
    
    # 运行表演
    for output in engine.run(max_steps=6, danmaku_sim=danmaku):
        pass
    
    print("\n✅ 测试完成！")
