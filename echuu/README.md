# Echuu - AI VTuber 自动直播系统

一个用于生成自然、即兴感的直播内容的 Python 库，通过从真实主播切片中学习表演模式。

## 概述

Echuu 是一个完整的 AI VTuber 自动直播系统，核心目标是生成**自然、即兴、有真实感**的直播内容。系统通过分析真实主播的表演模式，学习注意力转移、话语行为、故事结构等规律，并生成具有相似自然度的内容。

### 核心特性

- 🎭 **故事内核生成**: 基于"分享欲 + 反常 + 内心戏"的故事内核模式
- 🎨 **情绪复合**: 支持复杂情绪状态的建模和表达
- 💬 **弹幕互动**: 智能评估和响应实时弹幕
- 🎪 **即兴表演**: 支持跑题、结构破坏等自然行为
- 🧠 **记忆系统**: 维护剧情点、承诺、情绪轨迹等状态
- 🎙️ **语音合成**: 集成 TTS 客户端，支持实时语音生成

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from echuu import EchuuLiveEngine

# 创建引擎
engine = EchuuLiveEngine()

# 设置角色和话题
engine.setup(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦",
    background="前上班族，现全职主播"
)

# 运行表演
for step in engine.run(max_steps=15, play_audio=False, save_audio=True):
    print(f"[{step['stage']}] {step['speech']}")
    if step.get('inner_monologue'):
        print(f"  💭 {step['inner_monologue']}")
```

## 架构概览

Echuu 采用模块化设计，主要分为三个层次：

```
echuu/
├── core/           # 核心组件：故事内核、情绪、触发器等
├── generators/     # 生成器：剧本生成、示例采样
└── live/           # 实时表演：引擎、表演者、弹幕处理
```

## 核心组件

### Core 模块 (`echuu.core`)

#### StoryNucleus - 故事内核生成器

生成故事的核心模式，基于"分享欲 + 反常 + 内心戏"的公式。

```python
from echuu import StoryNucleus

nucleus = StoryNucleus()
story = nucleus.generate(
    topic="关于上司的八卦",
    persona="爱吐槽的女主播"
)
```

**核心模式**:
- `slippery_slope`: 滑坡谬误（小事变大事）
- `kindness_trap`: 善良陷阱（好心没好报）
- `anger_armor`: 愤怒盔甲（用愤怒掩盖脆弱）
- `choice_cost`: 选择代价（每个选择都有代价）
- `tiny_shame`: 微小羞耻（小事的羞耻感）
- `contradiction_reveal`: 矛盾揭示（自我矛盾）

#### EmotionMixer - 情绪混合器

处理复杂情绪状态，支持情绪复合和转换。

```python
from echuu import EmotionMixer, EmotionConfig

mixer = EmotionMixer()
config = EmotionConfig(
    primary="愤怒",
    secondary="委屈",
    intensity=0.7
)
emotion = mixer.mix(config)
```

#### TriggerBank - 触发词库

管理故事开场的触发模板，支持多种开场方式。

```python
from echuu import TriggerBank

bank = TriggerBank()
trigger = bank.sample_trigger("danmaku")
```

#### DigressionDB - 跑题数据库

注入自然的跑题内容，增加即兴感。

```python
from echuu import DigressionDB

db = DigressionDB()
digression = db.sample_digression(context="工作话题")
```

#### StructureBreaker - 结构破坏器

打破完美结构，生成非闭合、非升华的结尾。

```python
from echuu import StructureBreaker

breaker = StructureBreaker()
broken_script = breaker.break_structure(script_lines)
```

#### PatternAnalyzer - 模式分析器

从标注数据中学习真实主播的表演模式。

```python
from echuu import PatternAnalyzer

with open("data/annotated_clips.json", "r", encoding="utf-8") as f:
    clips = json.load(f)

analyzer = PatternAnalyzer(clips)
patterns = analyzer.analyze_patterns()
```

#### DramaAmplifier - 戏剧放大器

控制情绪强度和戏剧张力。

```python
from echuu import DramaAmplifier

amplifier = DramaAmplifier()
amplified = amplifier.amplify(script_line, intensity=0.8)
```

### Generators 模块 (`echuu.generators`)

#### ScriptGeneratorV4 - 剧本生成器

整合所有核心组件的主生成器，生成完整的直播剧本。

```python
from echuu import ScriptGeneratorV4

generator = ScriptGeneratorV4(llm_client, example_sampler)
script_lines = generator.generate(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦",
    background="前上班族，现全职主播"
)
```

**生成流程**:
1. Phase 0: 初始化创作环境
2. Phase 1: 生成故事内核（分享欲 + 反常 + 内心戏）
3. Phase 2: 生成完整剧本（包含跑题、结构破坏等）
4. Phase 3: 后处理和优化

#### ExampleSampler - 示例采样器

从真实切片中采样示例，用于 Few-shot 学习。

```python
from echuu import ExampleSampler

sampler = ExampleSampler("data/vtuber_raw_clips.jsonl")
examples = sampler.sample(topic="工作", count=3)
```

### Live 模块 (`echuu.live`)

#### EchuuLiveEngine - 主引擎

整合所有组件的核心引擎，提供完整的直播功能。

```python
from echuu import EchuuLiveEngine

engine = EchuuLiveEngine()
engine.setup(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦"
)

for step in engine.run(max_steps=15):
    # 处理每一步的表演结果
    pass
```

#### PerformerV3 - 表演者

执行剧本，处理弹幕，生成响应。

```python
from echuu import PerformerV3

performer = PerformerV3(llm_client, tts_client, danmaku_handler)
result = performer.perform_step(state, step_index)
```

#### DanmakuHandler - 弹幕处理器

评估和处理实时弹幕，决定是否响应。

```python
from echuu import DanmakuHandler, DanmakuEvaluator

evaluator = DanmakuEvaluator()
handler = DanmakuHandler(evaluator)

decision = handler.evaluate_danmaku(
    danmaku=danmaku,
    current_state=state
)
```

**评估机制**:
- `urgency`: 弹幕的紧急程度
- `cost`: 打断当前表演的代价
- `decision_value = urgency - cost`
  - 正数 → 响应弹幕
  - 负数 → 继续剧本

#### State 类

##### PerformanceState - 表演状态

维护整个表演的状态，包括剧本、记忆、弹幕队列等。

```python
from echuu import PerformanceState

state = PerformanceState(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦",
    script_lines=script_lines,
    memory=memory
)
```

##### PerformerMemory - 表演者记忆

维护剧情点、承诺、情绪轨迹等记忆状态。

```python
from echuu import PerformerMemory

memory = PerformerMemory()
memory.story_points["mentioned"].append("上司的八卦")
memory.promises.append({
    "text": "我会告诉你们细节",
    "fulfilled": False
})
```

##### Danmaku - 弹幕

弹幕数据模型。

```python
from echuu import Danmaku

danmaku = Danmaku.from_text("主播快说！", user="观众A")
```

## 高级用法

### 自定义回调

监听生成过程的各个阶段：

```python
def on_phase(msg):
    print(f"[Phase] {msg}")

engine.setup(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦",
    on_phase_callback=on_phase
)
```

### 实时弹幕注入

在表演过程中动态注入弹幕：

```python
from echuu import Danmaku

# 在表演过程中
danmaku = Danmaku.from_text("真的假的？", user="观众")
engine.state.danmaku_queue.append(danmaku)
```

### 自定义角色配置

```python
character_config = {
    "catchphrases": ["对吧", "我觉得"],
    "speech_style": "casual",
    "emotion_range": [0.3, 0.9]
}

engine.setup(
    name="六螺",
    persona="爱吐槽的女主播",
    topic="关于上司的八卦",
    character_config=character_config
)
```

## 数据格式

### 标注数据格式

```json
{
  "clip_id": "clip_001",
  "skeleton": "共情→自我经历→对比→建议→升华",
  "catchphrases": ["对吧", "我觉得"],
  "segments": [
    {
      "id": "seg_01",
      "start_time": 0,
      "end_time": 35,
      "text": "...",
      "attention_focus": "self",
      "speech_act": "opine",
      "trigger": "danmaku"
    }
  ]
}
```

### 剧本格式

```python
ScriptLineV4(
    id="line_01",
    text="我刚才看到这个，突然想起一个事...",
    stage="Hook",
    interruption_cost=0.3,
    key_info=["上司的八卦"],
    emotion_config={"primary": "兴奋", "intensity": 0.7}
)
```

## 配置

### 环境变量

在 `.env` 文件中配置：

```bash
# LLM API
ANTHROPIC_API_KEY=your_key
# 或
OPENAI_API_KEY=your_key

# TTS 配置
TTS_MODEL=qwen3-tts-flash-realtime
TTS_VOICE=Cherry
TTS_RESPONSE_FORMAT=pcm
TTS_SAMPLE_RATE=24000
```

## 设计理念

### 核心公式

**精彩 = 分享欲 + 反常 + 内心戏**

- **分享欲**: 有强烈的表达冲动
- **反常**: 打破常规，制造意外
- **内心戏**: 展现内心思考过程

### Interruption Cost 机制

决定是否响应弹幕的动态代价系统：

```python
decision_value = urgency - cost
```

- `urgency`: 弹幕的紧急程度（0-1）
- `cost`: 打断当前表演的代价（0-1）
- 正数 → 回应弹幕
- 负数 → 继续剧本

### Inner Monologue

让观众看到 AI 的"思考过程"，这是 echuu 区别于传统 AI 主播的核心特性。

## 示例

### 完整示例

```python
from echuu import EchuuLiveEngine

engine = EchuuLiveEngine()

# 设置
engine.setup(
    name="六螺",
    persona="25岁主播，活泼自嘲，喜欢分享生活经历",
    topic="关于上司的超劲爆八卦",
    background="目前在一家外企市场部工作"
)

# 运行
for step in engine.run(max_steps=15, save_audio=True):
    print(f"\n[{step['stage']}] {step['speech']}")
    
    if step.get('inner_monologue'):
        print(f"💭 {step['inner_monologue']}")
    
    if step.get('audio_url'):
        print(f"🎵 音频: {step['audio_url']}")
    
    if step.get('memory_snapshot'):
        memory = step['memory_snapshot']
        print(f"📝 剧情点: {memory['story_points']}")
        print(f"💭 承诺: {memory['promises']}")
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 相关文档

- [项目主 README](../README.md)
- [Web 控制台 README](../echuu-web/backend/README.md)
- [Qwen TTS 音色列表](../docs/qwen_tts_voices.md)
