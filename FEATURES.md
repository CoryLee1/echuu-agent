# 新功能说明

## 1. WAV 自动转 MP3 ✅

### 功能
音频录制完成后自动转换为 MP3 格式，减小文件大小约 **95%**。

### 效果对比
| 格式 | 文件大小 | 压缩率 |
|------|----------|--------|
| WAV | 14.9 MB | - |
| MP3 | 0.6 MB | 96% ↓ |

### 使用方法

#### 方法 1: 在代码中启用
```python
from echuu.live.engine import EchuuLiveEngine

engine = EchuuLiveEngine()
engine.setup(name="主播", persona="...", topic="...")

# 自动转换为 MP3
for result in engine.run(
    max_steps=10,
    save_audio=True,
    convert_to_mp3=True,  # 👈 启用 MP3 转换
):
    pass
```

#### 方法 2: 手动转换现有 WAV 文件
```python
from echuu.live.tts_client import convert_wav_to_mp3

# 将 WAV 转换为 MP3
mp3_path = convert_wav_to_mp3("audio.wav")
```

### 环境要求
- `pydub` - 音频处理库 (已安装)
- `ffmpeg` - 音频转换工具 (已安装)

---

## 2. 实时流式播放模式 ✅

### 功能
模拟真实直播体验：
- 🎙️ 串行播放每段音频
- ⏸️ 段落间自动添加自然停顿 (1-5秒)
- 🎭 根据剧本阶段智能调整停顿时长

### 停顿时长规则
| 剧本阶段 | 停顿时长 | 说明 |
|----------|----------|------|
| Hook | 1.5-3.0秒 | 开场：较短停顿，保持吸引力 |
| Build-up | 2.0-4.0秒 | 铺垫：中等停顿 |
| But | 0.5-1.5秒 | 转折点：很短停顿制造悬念 |
| Climax | 0.3-1.0秒 | 高潮：极短停顿，保持紧张 |
| Resolution | 3.0-5.0秒 | 结尾：较长停顿，自然收尾 |
| Inner-monologue | 2.5-4.5秒 | 独白：较长停顿，思考感 |

### 使用方法

#### 方法 1: 使用 demo.py
```bash
# 流式播放模式（播放音频 + 自然停顿）
python demo.py --streaming

# 仅生成 MP3（不播放）
python demo.py --mp3

# 两者都测试
python demo.py --both
```

#### 方法 2: 在代码中使用
```python
from echuu.live.engine import EchuuLiveEngine

engine = EchuuLiveEngine()
engine.setup(name="主播", persona="...", topic="...")

# 使用流式播放模式
engine.run_streaming(
    max_steps=10,
    save_audio=True,      # 保存音频
    convert_to_mp3=True,  # 转换为 MP3
)
```

### 环境要求
- `ffplay` - 音频播放工具 (来自 ffmpeg，已安装)

---

## 文件说明

### 新增文件
| 文件 | 说明 |
|------|------|
| `echuu-sdk-release/echuu/live/audio_player.py` | 音频播放器 - 支持自然停顿 |
| `demo.py` | 功能演示脚本 |
| `test_streaming.py` | 测试脚本 |

### 修改文件
| 文件 | 主要改动 |
|------|----------|
| `echuu-sdk-release/echuu/live/tts_client.py` | 添加 `convert_wav_to_mp3()` 函数和 MP3 转换支持 |
| `echuu-sdk-release/echuu/live/engine.py` | 添加 `run_streaming()` 方法和 MP3 转换参数 |

---

## 快速开始

### 1. 测试 MP3 转换
```bash
cd D:/vtuberclip/echuu-agent
python demo.py --mp3
```

### 2. 测试流式播放
```bash
python demo.py --streaming
```

### 3. 在代码中使用
```python
import sys
from pathlib import Path
sys.path.insert(0, 'echuu-sdk-release')

from echuu.live.engine import EchuuLiveEngine

engine = EchuuLiveEngine()
engine.setup(
    name="小梅",
    persona="活泼可爱的VTuber",
    topic="今天遇到的趣事",
    language="zh",
)

# 流式播放模式（推荐）
engine.run_streaming(max_steps=10, save_audio=True, convert_to_mp3=True)
```

---

## 注意事项

1. **音频播放**: 流式播放需要 `ffplay`，如果没有安装会自动跳过播放
2. **文件大小**: MP3 压缩率约 95-96%，大幅减少存储空间
3. **停顿时长**: 根据剧本阶段自动调整，更自然的直播效果
4. **兼容性**: 生成的 MP3 文件可在任何设备上播放

---

## 常见问题

**Q: 可以只转换 MP3 不播放吗？**
A: 可以，使用 `run()` 方法设置 `convert_to_mp3=True, play_audio=False`

**Q: 可以调整停顿时长吗？**
A: 可以，修改 `audio_player.py` 中的 `get_natural_pause()` 方法

**Q: MP3 比特率可以调整吗？**
A: 可以，使用 `convert_wav_to_mp3(wav_path, bitrate="192k")` 调整比特率
