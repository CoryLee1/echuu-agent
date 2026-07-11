# Echuu SDK - User Memory & Bonding System

## 概述

实现了基于用户档案的记忆和情感连接系统，让VTuber能够：
- 记住每个观众的名字和特点
- 根据互动频率建立情感连接
- 基于用户关系生成个性化回应

## 核心特性

### 1. 用户档案 (UserProfile)

```python
@dataclass
class UserProfile:
    username: str
    interaction_count: int          # 互动次数
    first_seen: Optional[datetime]  # 首次出现
    last_seen: Optional[datetime]   # 最近互动
    reaction_style: str            # 反应风格（幽默型/认真提问型/气氛组）
    bonding_level: int             # 情感连接等级
    total_sc_amount: int           # 累计打赏
    special_moments: List[str]     # 特殊时刻
```

### 2. 情感连接等级 (Bonding Levels)

| 等级 | 互动次数 | 关系描述 | 回应特点 |
|------|---------|---------|---------|
| 0 | 0-2 | 新观众 | 热情欢迎，简单回应 |
| 1 | 3-9 | 眼熟的观众 | "诶你又来了" |
| 2 | 10-19 | 老观众 | 熟悉语气，友好回应 |
| 3 | 20+ | 核心粉丝 | 亲切称呼，提到偏好，可跑题 |

### 3. 自动学习用户特点

系统自动分析弹幕内容，学习用户偏好：

```python
# 检测反应风格
if "哈哈" in danmaku.text:
    user.reaction_style = "幽默型"
elif danmaku.is_question():
    user.reaction_style = "认真提问型"
elif "加油" in danmaku.text:
    user.reaction_style = "气氛组"
```

### 4. 个性化LLM回应

根据用户关系生成不同回应：

```python
# 对核心粉丝"小明"发"哈哈哈哈"
LLM Response: "哈哈哈哈小明你每次都笑这么开心"

# 对老观众"小红"发"我第一次直播也紧张"
LLM Response: "对吧小红，那时候咱都一样"

# 对新观众发"六螺加油"
LLM Response: "谢谢谢谢！"
```

## 使用示例

### 基本使用

```python
from echuu.live.engine import EchuuLiveEngine
from echuu.live.state import Danmaku

engine = EchuuLiveEngine()
engine.setup(
    name="六螺",
    persona="25岁主播，活泼自嘲",
    topic="第一次直播的紧张经历",
    background="刚开始做全职主播"
)

# 创建带用户名的弹幕
danmaku_list = [
    Danmaku(text="哈哈哈哈", user="小明"),
    Danmaku(text="我第一次直播也紧张", user="小红"),
    Danmaku(text="六螺加油！", user="小明"),  # 小明的第2次互动
]

# 运行直播
for step in engine.run(danmaku_sim=danmaku_list):
    print(f"Speech: {step['speech']}")
    # 记忆系统会自动更新用户档案
```

### 查看用户档案

```python
# 获取特定用户
user = engine.state.memory.get_or_create_user("小明")
print(f"互动次数: {user.interaction_count}")
print(f"关系: {user.get_bonding_description()}")
print(f"风格: {user.reaction_style}")

# 查看所有用户
for username, user in engine.state.memory.user_profiles.items():
    print(f"{username}: {user.get_context_summary()}")

# 查看活跃用户上下文（用于LLM）
context = engine.state.memory.get_active_users_context(limit=5)
print(context)
# 输出: "活跃用户: 小明: 老观众（互动10次） | 风格=气氛组 | 小红: 新观众"
```

### 记忆显示

记忆系统会自动在输出中显示记住的观众：

```
+-------------------------------------------+
| AI 记忆状态                               |
+-------------------------------------------+
| 剧本: [######----] 5/8 (Climax)        |
| 弹幕: 已回应4条, 待回答0个问题           |
| 熟悉观众: 1人                        |
|   - 小明 (15次互动)           |
+-------------------------------------------+
```

## LLM Prompt 增强

弹幕回应时会自动包含用户上下文：

```
你是正在直播的VTuber主播六螺。

## 收到的弹幕
用户: 小明
关系: 老观众（互动10次）
内容: "哈哈哈哈"
类型: 情绪反应 - 觉得好笑

互动次数: 10
反应风格: 气氛组

## 你的记忆系统
**核心粉丝（互动20+次）**:
- 用亲切的称呼
- 提到他们的偏好
- 可以稍微跑题聊几句

**老观众（互动10+次）**:
- 熟悉的语气
- 友好的回应

**眼熟的观众（互动3+次）**:
- "诶你又来了"

[... LLM generates response based on this context ...]
```

## 代码变更摘要

### 修改的文件

1. **`state.py`** - 新增用户档案系统
   - `UserProfile` - 用户档案数据类
   - `PerformerMemory.user_profiles` - 用户字典
   - `get_or_create_user()` - 获取/创建用户
   - `update_user_from_danmaku()` - 更新互动记录
   - `get_active_users_context()` - 获取活跃用户上下文

2. **`response_generator.py`** - 基于用户关系生成回应
   - 移除硬编码模板
   - 使用LLM根据用户档案、关系、人格生成回应
   - 智能 fallback（仍基于用户关系）

3. **`performer.py`** - 集成用户记忆
   - 自动更新用户档案
   - 传递 persona 和 background 到回应生成器

## 未来扩展

### 可添加的特性

1. **持久化存储**
   ```python
   # 保存用户档案到文件
   engine.state.memory.save_profiles("users.json")

   # 下次直播加载
   engine.state.memory.load_profiles("users.json")
   ```

2. **更细致的用户分析**
   ```python
   user.preferred_topics = ["直播", "游戏", "美食"]
   user.activity_hours = ["晚上8-10点"]
   user.last_seen_days_ago = 7
   ```

3. **特殊互动记录**
   ```python
   user.special_moments = [
       "第一次SC (¥50)",
       "在直播间2小时",
       "提问被采纳3次"
   ]
   ```

4. **群体感**
   ```python
   # 检测好友/夫妻档
   if user1 and user2.always_appear_together():
       memory.user_groups["夫妻档"] = [user1, user2]

   # LLM可以: "诶小王小李你们俩又一起来啦"
   ```

## 测试

运行测试查看效果：

```bash
python test_user_memory.py
```

这会演示：
- 用户档案建立过程
- 情感连接等级提升
- 个性化回应生成
- 记忆显示功能
