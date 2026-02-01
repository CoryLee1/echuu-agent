# echuu-agent

AI VTuber 自动直播系统 - 从真实主播切片中学习表演模式

## 核心功能

1. **数据标注**: 从真实主播切片中提取表演模式（attention_focus, speech_act, trigger）
2. **模式分析**: 学习注意力转移、话语行为等规律
3. **自动生成**: 基于学习到的模式生成自然的直播内容
4. **Inner Monologue**: 让观众看到AI的"思考过程"

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 ANTHROPIC_API_KEY 或 OPENAI_API_KEY
```

TTS 使用 Qwen3 Realtime 时，请在 `.env` 设置 `TTS_MODEL` 与 `TTS_VOICE`，其余参数按需调整。

### 3. 运行交互式直播

```bash
# 交互式模式（推荐）
python workflow/backend/echuu_interactive.py

# 或使用预设测试脚本
python workflow/backend/echuu_live_engine.py
```

交互式模式支持：
- 输入人物名称、人设、背景
- 自定义直播主题或运行预设案例
- 自动保存剧本和音频文件

### 4. 运行数据标注

```bash
# 快速模式（不需要API Key，使用启发式规则）
python workflow/data-annotation-process/run_annotation.py --quick

# LLM精细标注（需要配置API Key）
python workflow/data-annotation-process/run_annotation.py
```### 4. 使用标注数据

在 Jupyter Notebook 中：

```python
import json

# 加载标注数据
with open("data/annotated_clips.json", "r", encoding="utf-8") as f:
    annotated_clips = json.load(f)

# 创建分析器
from workflow.jupyter_notebook.echuu_notebook import PatternAnalyzer, EchuuEngine
analyzer = PatternAnalyzer(annotated_clips)
```

## TTS 音色列表

详见 `docs/qwen_tts_voices.md`。

## 项目结构

```
echuu-agent/
├── .env                  # 环境变量配置（API Keys）
├── .env.example          # 环境变量模板
├── requirements.txt      # Python依赖
├── data/
│   ├── vtuber_raw_clips_*.jsonl    # 原始数据（30个切片）
│   └── annotated_clips.json        # 标注后数据
├── workflow/
│   ├── data-annotation-process/    # 数据标注流程
│   │   ├── data_annotation_pipeline.py  # 标注核心逻辑
│   │   ├── run_annotation.py            # 标注入口脚本
│   │   └── data_to_echuu_pipeline.ipynb # 交互式标注
│   ├── jupyter_notebook/
│   │   └── echuu_notebook (1).ipynb     # echuu引擎notebook
│   └── backend/
│       └── echuu_engine (1).py          # 后端引擎
└── .cursor/
    └── rules/
        └── project.mdc              # 项目规范
```## Pipeline 示例：从输入到输出

下面通过一个完整示例，展示 echuu 如何将用户输入转化为带表情标注的直播剧本。

### 用户输入

```python
engine.setup(
    name="六螺",
    persona="爱吐槽的前上班族女主播，说话直接，经常自嘲",
    topic="关于上司的超劲爆八卦",
    background="在互联网公司工作3年后辞职做全职主播"
)
```

---

### Phase -1: 故事内核分析 (StoryNucleus)

系统首先分析话题，确定故事的核心驱动力：

```
内核模式: 八卦爆料型
分享欲: "我知道一个超级劲爆的秘密，不说出来会憋死"
反常点: 身份反差 - 平时PUA别人的上司，居然被开除了
开场意图: 制造悬念，吊胃口
```

**输出**: 确定叙事框架和情绪基调

---

### Phase 0: 触发方式选择 (TriggerBank)

从触发库中选择自然的开场方式：

```
触发类型: thought_drift (思维漂移)
开场模板: "诶，你们知道吗，我突然想起来一件事..."
```

**输出**: 自然的故事入口

---

### Phase 1: 沉浸状态构建

模拟主播"边想边说"的状态：

```
我正在直播，刚才看到弹幕有人问我以前的工作，
突然想起那个天天PUA我们的前上司...
心情有点复杂，又想吐槽又觉得好笑。
准备用"你们猜怎么着"开场吊一下胃口。
```

**输出**: 第一人称沉浸视角

---

### Phase 2: 剧本生成 (ScriptGeneratorV4)

生成 8-10 个叙事单元，每个单元自动附带 PerformerCue：

```json
[
  {
    "id": "line_0",
    "text": "诶，你们知道吗，我上周发现了一件超级劲爆的事！",
    "stage": "Hook",
    "cost": 0.3,
    "cue": {
      "emotion": {"key": "happy", "intensity": 0.85},
      "gesture": {"clip": "react_surprised", "duration": 0.8},
      "look": {"target": "camera", "strength": 0.8},
      "blink": {"mode": "hold"}
    }
  },
  {
    "id": "line_1",
    "text": "就是...我前上司啊，那个天天PUA我们的人，居然...",
    "stage": "Build-up",
    "cost": 0.5,
    "cue": {
      "emotion": {"key": "neutral", "intensity": 0.6},
      "gesture": {"clip": "talk_gesture_medium", "duration": 2.0},
      "look": {"target": "down", "strength": 0.6},
      "pause": 0.3
    }
  },
  {
    "id": "line_2",
    "text": "他被公司开除了！哈哈哈哈！太解气了！",
    "stage": "Climax",
    "cost": 0.8,
    "cue": {
      "emotion": {"key": "happy", "intensity": 1.0},
      "gesture": {"clip": "react_laugh", "duration": 1.5},
      "look": {"target": "camera", "strength": 0.9},
      "blink": {"mode": "hold"},
      "beat": 0.5
    }
  },
  {
    "id": "line_3",
    "text": "好了不说了，反正就这么个事，看弹幕有人问什么...",
    "stage": "Resolution",
    "cost": 0.2,
    "cue": {
      "emotion": {"key": "relaxed", "intensity": 0.5},
      "gesture": {"clip": "idle_sway", "duration": 4.0},
      "look": {"target": "chat", "strength": 0.6}
    }
  }
]
```

---

### Phase 3: 结构破坏 (StructureBreaker)

注入真实主播的"不完美"特征：

- ❌ 删除升华结尾（"这件事让我明白..."）
- ✅ 添加跑题片段（"说到PUA，我想起之前..."）
- ✅ 数字模糊化（"500块" → "几百块吧"）
- ✅ 草草收尾（"反正就这样，下一个话题"）

---

### Phase 4: 实时表演 (PerformerV3)

逐行执行剧本，处理弹幕互动：

```
[Step 0] Hook [CONT]
  Speech: 诶，你们知道吗，我上周发现了一件超级劲爆的事！
  Cue: emotion=happy, gesture=react_surprised, look=camera

[Step 1] Build-up [CONT]
  Speech: 就是...我前上司啊，那个天天PUA我们的人，居然...
  Cue: emotion=neutral, gesture=talk_gesture_medium, look=down, pause=0.3s

[Step 2] Climax [CONT]
  Speech: 他被公司开除了！哈哈哈哈！太解气了！
  Cue: emotion=happy(1.0), gesture=react_laugh, beat=0.5s
  情绪断点: 完全破防 - 积压的不满释放

[Step 3] Resolution [TEASE]
  Danmaku: "为什么被开除？"
  Speech: 这个嘛...你们真想知道？那我下次直播详细说！好了不说了...
  Cue: emotion=relaxed, gesture=idle_sway, look=chat
```

---

### 输出：VRM 控制指令

PerformerCue 通过 VRMExpressionMapper 转换为前端可消费的指令：

```json
{
  "type": "expression",
  "blendShape": "happy",
  "weight": 1.0,
  "fadeIn": 0.15,
  "fadeOut": 0.25,
  "version": "vrm1"
}
```

```json
{
  "type": "gesture",
  "clip": "react_laugh",
  "duration": 1.5,
  "loop": false
}
```

前端（Unity/three-vrm）根据这些指令驱动虚拟形象的表情和动作。

---

### 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户输入                                 │
│  name="六螺", persona="...", topic="关于上司的八卦"              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase -1: StoryNucleus                                         │
│  → 分析话题 → 确定故事模式(八卦爆料) → 提取反常点                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 0: TriggerBank                                           │
│  → 选择触发类型(thought_drift) → 生成开场语                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: Immersion                                             │
│  → 构建第一人称沉浸状态 → 确定情绪基调                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: ScriptGeneratorV4                                     │
│  → LLM生成剧本 → 自动添加 PerformerCue (表情/动作/视线)          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ infer_emotion_from_text("太开心了！")                     │   │
│  │ → EmotionCue(key=HAPPY, intensity=1.0)                   │   │
│  │                                                           │   │
│  │ get_gesture_for_stage("Climax", "happy")                 │   │
│  │ → GestureCue(clip="react_laugh", duration=1.5)           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: StructureBreaker                                      │
│  → 删除升华 → 注入跑题 → 模糊数字 → 真实化处理                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 4: PerformerV3 + TTS                                     │
│  → 逐行执行 → 弹幕互动判断 → 语音合成                             │
│  → 输出 speech + audio + cue                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  输出: VRM 控制指令                                              │
│  → VRMExpressionMapper 转换                                     │
│  → 发送到 Unity/three-vrm 前端                                  │
│  → 驱动虚拟形象表情、动作、视线、口型                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心概念### 标注维度| 维度 | 说明 | 取值 |
|------|------|------|
| attention_focus | 注意力指向 | self, audience, specific, content, meta |
| speech_act | 话语行为 | narrate, opine, respond, elicit, pivot, backchannel |
| trigger | 触发源 | sc, danmaku, self, content, prior |

### Interruption Costechuu 的核心机制：决定是否响应弹幕的动态代价```python
decision_value = urgency - cost
# 正数 → 回应弹幕
# 负数 → 继续剧本
```

### Inner Monologue

让观众看到AI的"思考过程"，这是 echuu 区别于传统AI主播的核心特性## 数据格式

### 原始数据 (JSONL)

```json
{
  "clip_id": "clip_001",
  "source": "主播名",
  "language": "zh",
  "duration": 180,
  "title": "标题",
  "notes": {
    "trigger": "触发描述",
    "habit": "口癖",
    "structure": "叙事结构"
  },
  "transcript": [{"t": 0, "text": "..."}]
}
```### 标注数据 (JSON)```json
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

## 命令行工具```bash
# 查看帮助
python workflow/data-annotation-process/run_annotation.py --help

# 快速模式
python workflow/data-annotation-process/run_annotation.py --quick# 只标注部分数据（测试用）
python workflow/data-annotation-process/run_annotation.py --max-clips 5

# 检查配置
python workflow/data-annotation-process/run_annotation.py --dry-run

# 指定输出路径
python workflow/data-annotation-process/run_annotation.py -o custom_output.json
```

## 许可证

MIT License