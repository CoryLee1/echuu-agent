# Echuu SDK

AI VTuber 自动直播系统 Python SDK - 从真实主播切片中学习表演模式。

## 特性

- 🎭 **故事内核生成** - 基于分享欲 + 反常 + 内心戏
- 🎨 **情绪复合** - 支持复杂情绪状态建模
- 💬 **智能弹幕互动** - 动态评估和响应弹幕
- 🧠 **记忆系统** - 维护剧情点、承诺、情绪轨迹
- 🌍 **多语言支持** - 中文、英文、日文自动检测
- 🎙️ **TTS 集成** - Qwen3 Realtime API
- 📦 **VRM 控制** - 表情、动作、视线、口型

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

```python
from echuu.live.engine import EchuuLiveEngine

engine = EchuuLiveEngine()
engine.setup(
    name="小梅",
    persona="活泼可爱的VTuber",
    topic="食堂打饭遇到的趣事",
    language="zh"
)

# 运行表演
for result in engine.run(max_steps=10):
    print(result["speech"])  # 剧本文本
    print(result["cue"])     # VRM 控制指令
```

## 流式播放模式

```python
# 串行播放音频，段落间有自然停顿
engine.run_streaming(
    max_steps=10,
    save_audio=True,
    convert_to_mp3=True
)
```

## 模块概览

```
echuu/
├── core/          # 核心组件（故事内核、情绪、触发器）
├── generators/    # 生成器（剧本、示例采样）
├── live/          # 实时表演（引擎、TTS、弹幕处理）
└── vrm/           # VRM 控制（表情映射、预设）
```

## 主要类

| 模块 | 类名 | 说明 |
|------|------|------|
| `live` | `EchuuLiveEngine` | 主引擎 |
| `live` | `PerformerV3` | 表演执行 |
| `live` | `DanmakuHandler` | 弹幕处理 |
| `live` | `TTSClient` | 语音合成 |
| `live` | `StreamSimulator` | 流式播放 |
| `generators` | `ScriptGeneratorV4` | 剧本生成 |
| `core` | `StoryNucleus` | 故事内核 |
| `core` | `EmotionMixer` | 情绪混合 |
| `core` | `PatternAnalyzer` | 模式分析 |

## 配置

环境变量（`.env`）：

```bash
# Gemini 3
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3-flash-preview

# Qwen TTS
DASHSCOPE_API_KEY=your-key
TTS_MODEL=qwen3-tts-flash-realtime
TTS_VOICE=Cherry
```

## 输出格式

### 剧本（JSON）

```json
{
  "metadata": {"name": "小梅", "topic": "..."},
  "script": [
    {
      "id": "line_0",
      "text": "不知道为什么我突然想起...",
      "stage": "Hook",
      "cue": {
        "emotion": {"key": "neutral", "intensity": 0.7},
        "gesture": {"clip": "react_think"},
        "look": {"target": "camera"}
      }
    }
  ]
}
```

### VRM 指令

```json
{
  "type": "expression",
  "blendShape": "happy",
  "weight": 0.85,
  "fadeIn": 0.15,
  "fadeOut": 0.25
}
```

## 许可证

Apache-2.0
