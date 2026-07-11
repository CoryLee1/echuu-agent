"""echuu 三大内容模式（预生产管线）。

每个模式是一个 produce_*_events 函数：
输入角色/主题/模式专属 source，输出 step 事件列表（含音频字节或 audio_url），
由 live_service 的统一表演循环消费。

- storytelling: 默认模式，走 EchuuLiveEngine 现有路径（不在本包内）
- reaction:     看视频边看边反应（qwen3.5-omni 时间轴标注 → 反应脚本 → TTS）
- singing_learn: 学唱一首歌（Demucs 分离 → RVC 转换 → 做旧 → 三段式编排）
"""

MODES = ("storytelling", "reaction", "singing_learn")
