# ECHUU Agent 架构说明文档

## 📋 目录

1. [系统概述](#系统概述)
2. [核心构成](#核心构成)
3. [工作流程](#工作流程)
4. [数据流](#数据流)
5. [缺失功能：VRM 动作映射](#缺失功能vrm-动作映射)
6. [实现建议](#实现建议)

---

## 系统概述

ECHUU Agent 是一个 AI VTuber 自动直播系统，核心目标是生成**自然、即兴、有真实感**的直播内容。系统通过分析真实主播的表演模式，学习注意力转移、话语行为、故事结构等规律，并生成具有相似自然度的内容。

### 核心公式

**精彩 = 分享欲 + 反常 + 内心戏**

- **分享欲**: 有强烈的表达冲动
- **反常**: 打破常规，制造意外
- **内心戏**: 展现内心思考过程

---

## 核心构成

### 1. Core 模块 (`echuu/core/`)

核心组件负责生成故事内核、处理情绪、管理触发器等基础功能。

#### 1.1 StoryNucleus - 故事内核生成器

**位置**: `echuu/core/story_nucleus.py`

**功能**: 生成故事的核心模式，基于"分享欲 + 反常 + 内心戏"的公式。

**核心模式**:
- `slippery_slope`: 滑坡谬误（小事变大事）
- `kindness_trap`: 善良陷阱（好心没好报）
- `anger_armor`: 愤怒盔甲（用愤怒掩盖脆弱）
- `choice_cost`: 选择代价（每个选择都有代价）
- `tiny_shame`: 微小羞耻（小事的羞耻感）
- `contradiction_reveal`: 矛盾揭示（自我矛盾）

**输出**: 故事内核字典，包含分享欲、反常点、结构等信息。

#### 1.2 EmotionMixer - 情绪混合器

**位置**: `echuu/core/emotion_mixer.py`

**功能**: 处理复杂情绪状态，支持情绪复合和转换。

**特性**:
- 主情绪 + 次情绪组合
- 情绪掩蔽（用 A 情绪掩盖 B 情绪）
- 情绪强度控制

**输出**: `EmotionConfig` 对象，包含主情绪、次情绪、掩蔽情绪、强度等。

#### 1.3 TriggerBank - 触发词库

**位置**: `echuu/core/trigger_bank.py`

**功能**: 管理故事开场的触发模板，支持多种开场方式。

**触发类型**:
- `sensory_trigger`: 感官触发回忆
- `pain_point_hit`: 被戳到痛点
- `absurdity_overflow`: 太离谱必须吐槽
- `secret_confession`: 想坦白
- `thought_drift`: 思维漂移

#### 1.4 DigressionDB - 跑题数据库

**位置**: `echuu/core/digression_db.py`

**功能**: 注入自然的跑题内容，增加即兴感。

#### 1.5 StructureBreaker - 结构破坏器

**位置**: `echuu/core/structure_breaker.py`

**功能**: 打破完美结构，生成非闭合、非升华的结尾。

#### 1.6 PatternAnalyzer - 模式分析器

**位置**: `echuu/core/pattern_analyzer.py`

**功能**: 从标注数据中学习真实主播的表演模式。

#### 1.7 DramaAmplifier - 戏剧放大器

**位置**: `echuu/core/drama_amplifier.py`

**功能**: 控制情绪强度和戏剧张力。

---

### 2. Generators 模块 (`echuu/generators/`)

生成器模块负责整合所有核心组件，生成完整的直播剧本。

#### 2.1 ScriptGeneratorV4 - 剧本生成器

**位置**: `echuu/generators/script_generator_v4.py`

**功能**: 整合所有核心组件的主生成器，生成完整的直播剧本。

**生成流程**:
1. **Phase -1**: 确定故事内核（分享欲 + 反常 + 内心戏）
2. **Phase 0**: 选择触发方式
3. **Phase 1**: 建立沉浸状态
4. **Phase 2**: LLM 生成完整剧本（8-10 个叙事单元）
5. **Phase 3**: 后处理和优化（结构破坏、跑题注入）

**输出**: `List[ScriptLineV4]`，每个元素包含：
- `id`: 台词 ID
- `text`: 台词文本（80-120 字）
- `stage`: 叙事阶段（Hook/Build-up/Climax/Resolution）
- `interruption_cost`: 中断代价（0.0-1.0）
- `key_info`: 关键信息列表
- `disfluencies`: 认知特征（数字模糊、自我修正等）
- `emotion_break`: 情绪断点（可选，包含 level 和 trigger）
- `emotion_config`: 情绪配置（可选）

#### 2.2 ExampleSampler - 示例采样器

**位置**: `echuu/generators/example_sampler.py`

**功能**: 从真实切片中采样示例，用于 Few-shot 学习。

---

### 3. Live 模块 (`echuu/live/`)

实时表演模块负责执行剧本、处理弹幕、生成响应。

#### 3.1 EchuuLiveEngine - 主引擎

**位置**: `echuu/live/engine.py`

**功能**: 整合所有组件的核心引擎，提供完整的直播功能。

**主要方法**:
- `setup()`: 初始化并生成剧本
- `run()`: 执行表演（生成器模式）

**工作模式**:
- **Phase 1**: 预生成完整剧本（默认使用 V4.1）
- **Phase 2**: 实时表演 + 记忆系统 + 弹幕互动

#### 3.2 PerformerV3 - 表演者

**位置**: `echuu/live/performer.py`

**功能**: 执行剧本，处理弹幕，生成响应。

**核心方法**:
- `step()`: 执行一步表演

**处理流程**:
1. 检查弹幕队列
2. 评估是否响应弹幕（`decision_value = urgency - cost`）
3. 生成台词（继续剧本或回应弹幕）
4. 更新记忆状态
5. 生成 TTS 音频
6. 返回结果

**输出数据结构**:
```python
{
    "speech": str,              # 台词文本
    "action": str,              # 动作类型（continue/tease/jump/improvise/end）
    "stage": str,               # 叙事阶段
    "step": int,                # 步骤编号
    "audio": bytes,             # TTS 音频数据（可选）
    "emotion_break": dict,      # 情绪断点（可选）
    "disfluencies": list,       # 认知特征
    "memory_display": str,      # 记忆状态显示
    "line_idx": int,            # 当前台词索引
    # ... 其他字段
}
```

#### 3.3 DanmakuHandler - 弹幕处理器

**位置**: `echuu/live/danmaku.py`

**功能**: 评估和处理实时弹幕，决定是否响应。

**评估机制**:
- `urgency`: 弹幕的紧急程度（0-1）
- `cost`: 打断当前表演的代价（0-1）
- `decision_value = urgency - cost`
  - 正数 → 响应弹幕
  - 负数 → 继续剧本

#### 3.4 ResponseGenerator - 响应生成器

**位置**: `echuu/live/response_generator.py`

**功能**: 使用 LLM 生成自然的弹幕回应。

#### 3.5 State 类

**位置**: `echuu/live/state.py`

**数据结构**:
- `PerformanceState`: 表演状态
  - `script_lines`: 剧本台词列表
  - `current_line_idx`: 当前台词索引
  - `memory`: 记忆系统
  - `danmaku_queue`: 弹幕队列
- `PerformerMemory`: 表演者记忆
  - `script_progress`: 剧本进度
  - `danmaku_memory`: 弹幕记忆
  - `promises`: 承诺列表
  - `story_points`: 剧情点
  - `emotion_track`: 情绪轨迹

#### 3.6 TTSClient - TTS 客户端

**位置**: `echuu/live/tts_client.py`

**功能**: 调用 TTS API 生成语音。

**当前支持**: Qwen TTS（通义千问）

#### 3.7 LLMClient - LLM 客户端

**位置**: `echuu/live/llm_client.py`

**功能**: 调用 LLM API 生成文本。

**当前支持**: Anthropic Claude、OpenAI GPT

---

## 工作流程

### 完整流程概览

```
用户输入（角色 + 话题）
        ↓
┌───────────────────────────────────┐
│    Phase 1: 剧本生成阶段          │
├───────────────────────────────────┤
│ Phase -1: StoryNucleus            │
│   └─> 生成故事内核                │
│ Phase  0: TriggerBank             │
│   └─> 选择触发方式                │
│ Phase  1: 建立沉浸状态            │
│   └─> EmotionMixer 配置情绪       │
│ Phase  2: ScriptGeneratorV4        │
│   └─> LLM 生成完整剧本            │
│ Phase  3: StructureBreaker        │
│   └─> 结构破坏和优化              │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│    Phase 2: 实时表演阶段          │
├───────────────────────────────────┤
│ For each script line:             │
│   1. PerformerV3.step()          │
│      ├─> 检查弹幕队列             │
│      ├─> DanmakuHandler 评估      │
│      │   └─> decision_value       │
│      ├─> 生成台词                 │
│      │   ├─> 继续剧本              │
│      │   └─> 或回应弹幕            │
│      ├─> 更新记忆状态             │
│      ├─> TTSClient 生成音频        │
│      └─> 返回结果                 │
│   2. 通过 WebSocket 推送到前端    │
│   3. 前端播放音频和显示内容       │
└───────────────────────────────────┘
```

### 详细流程说明

#### Phase 1: 剧本生成

1. **StoryNucleus.generate_nucleus()**
   - 输入: 话题、角色配置
   - 输出: 故事内核（分享欲、反常点、结构模式）

2. **TriggerBank.sample()**
   - 输入: 角色配置、语言
   - 输出: 触发模板（填充后的开场白）

3. **EmotionMixer.mix()**
   - 输入: 主情绪、语言
   - 输出: 情绪配置（主情绪、次情绪、掩蔽、强度）

4. **ScriptGeneratorV4.generate()**
   - 输入: 角色信息、话题、故事内核、触发方式、情绪配置
   - 过程:
     - 构建 Few-shot 示例
     - 调用 LLM 生成剧本
     - 解析 JSON 输出
   - 输出: `List[ScriptLineV4]`

5. **StructureBreaker.break_structure()**
   - 输入: 剧本列表
   - 过程:
     - 删除升华结尾
     - 注入跑题内容
     - 添加非闭合结尾
   - 输出: 优化后的剧本列表

#### Phase 2: 实时表演

1. **EchuuLiveEngine.run()**
   - 遍历剧本的每一行
   - 对每一行调用 `PerformerV3.step()`

2. **PerformerV3.step()**
   - 检查弹幕队列
   - 对每个弹幕调用 `DanmakuHandler.handle()`
   - 选择优先级最高的弹幕（如果有）
   - 决策:
     - 如果 `decision_value > 0`: 回应弹幕
       - 调用 `ResponseGenerator.generate_response()`
       - 生成回应台词
     - 否则: 继续剧本
       - 使用当前剧本台词
   - 更新记忆状态
   - 生成 TTS 音频
   - 返回结果字典

3. **结果推送**
   - 通过 WebSocket 推送到前端
   - 前端接收并显示

---

## 数据流

### 输入数据

```python
{
    "name": str,              # 角色名称
    "persona": str,           # 人设描述
    "background": str,        # 背景信息
    "topic": str,             # 话题
    "language": str,          # 语言（默认 "zh"）
    "character_config": dict  # 角色配置（可选）
}
```

### 中间数据

#### ScriptLineV4

```python
{
    "id": str,                    # 台词 ID
    "text": str,                  # 台词文本（80-120 字）
    "stage": str,                 # 叙事阶段（Hook/Build-up/Climax/Resolution）
    "interruption_cost": float,   # 中断代价（0.0-1.0）
    "key_info": List[str],        # 关键信息列表
    "disfluencies": List[str],    # 认知特征
    "emotion_break": dict,        # 情绪断点（可选）
    "emotion_config": dict        # 情绪配置（可选）
}
```

#### PerformerMemory

```python
{
    "script_progress": {
        "current_line": int,
        "total_lines": int,
        "current_stage": str
    },
    "danmaku_memory": {
        "received": List[str],
        "responded": List[str]
    },
    "promises": List[dict],
    "story_points": {
        "mentioned": List[str],
        "upcoming": List[str]
    },
    "emotion_track": List[dict]
}
```

### 输出数据

#### Step Result

```python
{
    "speech": str,              # 台词文本
    "action": str,              # 动作类型
    "stage": str,               # 叙事阶段
    "step": int,                # 步骤编号
    "audio": bytes,             # TTS 音频数据
    "audio_url": str,           # 音频文件 URL（Web 端）
    "emotion_break": dict,      # 情绪断点
    "disfluencies": List[str],  # 认知特征
    "memory_snapshot": dict,    # 记忆快照
    "line_idx": int,            # 当前台词索引
    "danmaku": str,             # 回应的弹幕（如果有）
    # ... 其他字段
}
```

---

## 缺失功能：VRM 动作映射

### 当前状态

**✅ 已实现**:
- 台词文本生成
- 情绪信息提取（`emotion_break`, `emotion_config`）
- 叙事阶段识别（`stage`）
- 动作类型识别（`action`）
- TTS 音频生成

**❌ 未实现**:
- **VRM Blendshape 映射**: 将情绪信息映射到 VRM 表情 blendshape
- **人物动作映射**: 将台词、情绪、动作映射到 VRM 动画/动作
- **口型同步**: 基于音频生成口型动画数据
- **实时控制接口**: 与 VRM 渲染引擎的实时通信

### 缺失的数据结构

当前系统输出的 `step_result` 中**没有**以下字段：

```python
{
    # ❌ 缺失的字段
    "blendshapes": dict,        # VRM blendshape 权重
    "animations": List[str],    # 动画名称列表
    "gestures": List[str],      # 手势列表
    "lip_sync": dict,           # 口型同步数据
    "body_motion": dict,        # 身体动作数据
}
```

### 需要映射的信息

系统已经生成了丰富的语义信息，但**没有转换为 VRM 控制数据**：

1. **情绪 → Blendshape**
   - `emotion_break.level` → 表情强度
   - `emotion_config.primary` → 基础表情（开心/生气/悲伤等）
   - `emotion_config.secondary` → 复合表情
   - `emotion_config.mask` → 掩蔽表情

2. **叙事阶段 → 动作**
   - `stage: "Hook"` → 吸引注意力的动作
   - `stage: "Climax"` → 强调性动作
   - `stage: "Resolution"` → 放松动作

3. **动作类型 → 手势**
   - `action: "tease"` → 调皮手势
   - `action: "improvise"` → 即兴手势
   - `action: "jump"` → 快速切换动作

4. **台词内容 → 口型**
   - 需要音频分析或文本到音素映射
   - 生成口型动画序列

---

## 实现建议

### 方案 1: 情绪到 Blendshape 映射模块

**位置**: `echuu/live/vrm_mapper.py`（新建）

**功能**: 将情绪信息映射到 VRM blendshape 权重。

**实现思路**:

```python
class VRMBlendshapeMapper:
    """VRM Blendshape 映射器"""
    
    # VRM 标准 blendshape 名称
    BLENDSHAPES = {
        "happy": "Happy",
        "angry": "Angry",
        "sad": "Sad",
        "surprised": "Surprised",
        "relaxed": "Relaxed",
        # ... 更多
    }
    
    def map_emotion_to_blendshapes(
        self,
        emotion_config: dict,
        emotion_break: dict = None,
        stage: str = None
    ) -> dict:
        """
        将情绪配置映射到 blendshape 权重
        
        返回:
        {
            "Happy": 0.3,
            "Angry": 0.0,
            "Sad": 0.1,
            ...
        }
        """
        blendshapes = {}
        
        # 基础情绪映射
        primary = emotion_config.get("primary", "neutral")
        intensity = emotion_config.get("intensity", 0.5)
        
        # 映射主情绪
        if primary == "开心":
            blendshapes["Happy"] = intensity
        elif primary == "生气":
            blendshapes["Angry"] = intensity
        # ... 更多映射
        
        # 情绪断点增强
        if emotion_break:
            level = emotion_break.get("level", 0)
            boost = level * 0.2  # Level 1: +0.2, Level 2: +0.4, Level 3: +0.6
            for key in blendshapes:
                blendshapes[key] = min(1.0, blendshapes[key] + boost)
        
        # 阶段调整
        if stage == "Climax":
            # 高潮阶段增强所有表情
            for key in blendshapes:
                blendshapes[key] = min(1.0, blendshapes[key] * 1.2)
        
        return blendshapes
```

### 方案 2: 动作映射模块

**位置**: `echuu/live/animation_mapper.py`（新建）

**功能**: 将叙事阶段和动作类型映射到动画名称。

**实现思路**:

```python
class AnimationMapper:
    """动画映射器"""
    
    # 动画映射规则
    STAGE_ANIMATIONS = {
        "Hook": ["attention", "wave"],
        "Build-up": ["thinking", "gesture"],
        "Climax": ["excited", "emphasize"],
        "Resolution": ["relax", "nod"]
    }
    
    ACTION_ANIMATIONS = {
        "tease": ["tease", "wink"],
        "improvise": ["gesture", "think"],
        "jump": ["quick_move"],
        "continue": ["idle", "talk"]
    }
    
    def map_to_animations(
        self,
        stage: str,
        action: str,
        emotion_level: int = 0
    ) -> List[str]:
        """映射到动画名称列表"""
        animations = []
        
        # 阶段动画
        if stage in self.STAGE_ANIMATIONS:
            animations.extend(self.STAGE_ANIMATIONS[stage])
        
        # 动作动画
        if action in self.ACTION_ANIMATIONS:
            animations.extend(self.ACTION_ANIMATIONS[action])
        
        # 情绪增强动画
        if emotion_level >= 2:
            animations.append("emotion_boost")
        
        return animations
```

### 方案 3: 口型同步模块

**位置**: `echuu/live/lip_sync.py`（新建）

**功能**: 基于音频或文本生成口型动画数据。

**实现思路**:

```python
class LipSyncGenerator:
    """口型同步生成器"""
    
    # 音素到口型的映射（简化版）
    PHONEME_TO_VISEME = {
        "a": "A",
        "i": "I",
        "u": "U",
        "e": "E",
        "o": "O",
        "m": "M",
        "p": "P",
        "b": "B",
        # ... 更多映射
    }
    
    def generate_lip_sync(
        self,
        audio_data: bytes,
        sample_rate: int = 24000
    ) -> List[dict]:
        """
        基于音频生成口型序列
        
        返回:
        [
            {"time": 0.0, "viseme": "A", "intensity": 0.8},
            {"time": 0.1, "viseme": "I", "intensity": 0.6},
            ...
        ]
        """
        # 方案 1: 使用音频分析库（如 librosa）提取音素
        # 方案 2: 使用文本到音素转换（TTS 可能提供）
        # 方案 3: 使用预训练的 lip sync 模型
        
        pass
```

### 方案 4: 集成到 PerformerV3

**修改**: `echuu/live/performer.py`

在 `PerformerV3.step()` 方法中添加 VRM 映射：

```python
def step(self, state: PerformanceState, new_danmaku: Optional[List[Danmaku]] = None) -> Dict:
    # ... 现有代码 ...
    
    # 生成 VRM 控制数据
    vrm_mapper = VRMBlendshapeMapper()
    animation_mapper = AnimationMapper()
    lip_sync_gen = LipSyncGenerator()
    
    # 映射 blendshapes
    blendshapes = vrm_mapper.map_emotion_to_blendshapes(
        current_line.emotion_config or {},
        current_line.emotion_break,
        current_line.stage
    )
    
    # 映射动画
    animations = animation_mapper.map_to_animations(
        current_line.stage,
        output.get("action", "continue"),
        current_line.emotion_break.get("level", 0) if current_line.emotion_break else 0
    )
    
    # 生成口型同步（如果有音频）
    lip_sync = None
    if audio:
        lip_sync = lip_sync_gen.generate_lip_sync(audio)
    
    # 添加到输出
    output["blendshapes"] = blendshapes
    output["animations"] = animations
    output["lip_sync"] = lip_sync
    
    return output
```

### 方案 5: WebSocket 扩展

**修改**: `echuu-web/backend/routers/websocket.py`

在 WebSocket 消息中添加 VRM 数据：

```python
await state.broadcast({
    "type": "step",
    "data": {
        **result,
        "vrm": {
            "blendshapes": result.get("blendshapes", {}),
            "animations": result.get("animations", []),
            "lip_sync": result.get("lip_sync", [])
        }
    }
})
```

### 方案 6: 前端 VRM 渲染

**新建**: `echuu-web/frontend/src/components/VRMViewer.tsx`

使用 Three.js + @pixiv/three-vrm 渲染 VRM 模型：

```typescript
import { VRM } from '@pixiv/three-vrm';

class VRMViewer {
  private vrm: VRM;
  
  updateBlendshapes(blendshapes: Record<string, number>) {
    // 更新 blendshape 权重
    Object.entries(blendshapes).forEach(([name, weight]) => {
      this.vrm.blendShapeProxy?.setValue(name, weight);
    });
  }
  
  playAnimation(name: string) {
    // 播放动画
    // ...
  }
  
  updateLipSync(lipSync: Array<{time: number, viseme: string}>) {
    // 更新口型
    // ...
  }
}
```

---

## 总结

### 当前架构优势

1. ✅ **完整的语义理解**: 系统能够理解情绪、阶段、动作类型
2. ✅ **丰富的上下文信息**: 记忆系统、情绪轨迹、剧情点
3. ✅ **实时交互能力**: 弹幕处理、动态响应
4. ✅ **模块化设计**: 易于扩展和修改

### 缺失的关键环节

1. ❌ **语义到视觉的映射**: 情绪 → Blendshape，动作 → 动画
2. ❌ **口型同步**: 音频 → 口型动画
3. ❌ **实时渲染**: VRM 模型加载和控制
4. ❌ **动作编排**: 多个动画的平滑过渡

### 实现优先级

1. **高优先级**: 情绪到 Blendshape 映射（核心功能）
2. **中优先级**: 动作映射、口型同步
3. **低优先级**: 高级动画编排、物理模拟

---

## 参考资料

- [VRM Specification](https://vrm.dev/)
- [Three.js VRM Loader](https://github.com/pixiv/three-vrm)
- [Lip Sync 技术](https://github.com/Rudrabha/Wav2Lip)
- [Blendshape 标准](https://docs.unity3d.com/Manual/BlendShapes.html)

---

*文档版本: 1.0*  
*最后更新: 2026-01-30*
