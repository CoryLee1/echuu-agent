# 多语言支持方案分析

## 1. 语言检测机制

### 需要检测的场景
- **纯中文**: "哈哈哈哈"
- **纯英文**: "lololol that's funny"
- **纯日文**: "あははは"
- **中式英语**: "好好笑good good"
- **中英夹杂**: "这个故事so funny，我笑死"
- **中日夹杂**: "本当に面白い，太好笑了"

### 检测策略
```python
def detect_language(text: str) -> LanguageProfile:
    """
    检测文本语言类型

    Returns:
        LanguageProfile {
            primary: "zh" | "en" | "ja" | "mixed",
            secondary: "zh" | "en" | "ja" | None,
            dialect: "shanghai" | "cantonese" | None,
            confidence: float
        }
    """
```

## 2. VTuber语言能力配置

### 配置结构
```python
@dataclass
class VTuberLanguageProfile:
    """VTuber的语言能力和风格"""

    # 语言能力等级
    native: str                    # 母语: "zh-CN"
    fluent: List[str]              # 流利: ["en-US", "ja-JP"]
    basic: List[str]               # 基础: ["yue-HK"] (粤语等)

    # 方言/口癖风格
    regional_style: Optional[str]   # "上海话" | "粤语" | "北京话"
    accent_level: float            # 方言程度 0-1

    # 语言混用习惯
    code_switching: bool           # 是否会中英夹杂
    code_switching_rate: float     # 夹杂频率 0-1

    # 口癖/口头禅（多语言）
    catchphrases: Dict[str, List[str]] = field(default_factory=dict)
    # {
    #     "zh-CN": ["诶", "然后", "对吧"],
    #     "en-US": ["like", "you know", "literally"],
    #     "shanghai": ["伐", "嗲", "阿拉"],
    #     "cantonese": ["架", "靓仔", "真系"]
    }
```

### 配置示例

#### 上海人设
```python
shanghai_streamer = VTuberLanguageProfile(
    native="zh-CN",
    fluent=["en-US"],
    basic=["zh-shanghai"],
    regional_style="上海话",
    accent_level=0.7,
    code_switching=True,
    code_switching_rate=0.3,
    catchphrases={
        "zh-CN": ["诶", "然后", "对吧"],
        "shanghai": ["伐", "嗲", "阿拉", "噶"],
        "en-US": ["okay", "alright", "fantastic"],
    }
)

# 回应示例:
# - 观众: "好好笑"
#   回应: "真的噶伐，阿拉笑得不行"
# - 观众: "that's so funny"
#   回应: "对啊对啊，like真的好笑"
```

#### 广东人设
```python
cantonese_streamer = VTuberLanguageProfile(
    native="zh-CN",
    fluent=["en-US", "ja-JP"],
    basic=["yue-HK"],  # 粤语
    regional_style="粤语",
    accent_level=0.6,
    code_switching=True,
    code_switching_rate=0.4,
    catchphrases={
        "zh-CN": ["诶", "然后"],
        "yue-HK": ["架", "靓仔", "真系", "冇问题"],
        "en-US": ["awesome", "let's go"],
    }
)

# 回应示例:
# - 观众: "加油"
#   回应: "多谢晒靓仔支持！"
# - 观众: "六螺加油"
#   回应: "唔该！let's do this"
```

#### 国际人设（中日英流利）
```python
international_streamer = VTuberLanguageProfile(
    native="zh-CN",
    fluent=["en-US", "ja-JP", "zh-CN"],
    basic=[],
    regional_style=None,
    accent_level=0.1,
    code_switching=True,
    code_switching_rate=0.5,
    catchphrases={
        "zh-CN": ["诶", "然后", "对吧"],
        "en-US": ["like", "you know", "literally"],
        "ja-JP": ["あ", "それで", "ね"],
    }
)

# 回应示例:
# - 观众: "面白い"
#   回应: "ありがとう！本当に嬉しい"
# - 观众: "that's funny"
#   回应: "对啊对啊，like really funny"
```

## 3. 语言回应策略

### 策略矩阵

| 观众语言 | VTuber能力 | 回应策略 | 示例 |
|---------|-----------|---------|------|
| 中文 | 母语+方言 | 纯中文+方言口癖 | "诶你又来了伐" |
| 中文 | 母语+code-switching | 中文为主+偶尔英语 | "对啊对啊，like真的很好笑" |
| 英文 | 流利英语 | 纯英文回应 | "You're back! That's awesome" |
| 英文 | 基础英语 | 中式英语/简单英语 | "Yes yes, very good thank you" |
| 日文 | 流利日语 | 纯日文回应 | "あ、また来たね" |
| 日文 | 基础日语 | 简单日文+中文 | "ありがとう！真的好开心" |
| 中英混合 | 流利双语 | 匹配混合风格 | "哈哈yeah真的super funny" |
| 中英混合 | 中式英语 | 保留中式风格 | "对啊good good，笑死我了" |
| 中日混合 | 流利双语 | 匹配混合风格 | "はい、真的好开心啊" |

### 方言/口癖实现方式

#### 词库式 (适合上海话、粤语)
```python
REGIONAL_WORD_REPLACE = {
    "shanghai": {
        "是": "是伐",
        "的": "噶",
        "我们": "阿拉",
        "很好": "老好",
    }
}

# 应用替换
def apply_shanghai_accent(text: str, rate: float = 0.3) -> str:
    """随机替换部分词为上海话"""
    for original, shanghai in REGIONAL_WORD_REPLACE["shanghai"].items():
        if random.random() < rate:
            text = text.replace(original, shanghai)
    return text
```

#### 口癖式 (适合北京话、网络用语)
```python
BEIJING_MANNERISMS = {
    "suffix": ["呢", "啊", "呗", "嘿"],
    "prefix": ["我说", "诶", "那个"],
    "filler": ["就是", "咱们", "这"]
}

def apply_beijing_style(text: str) -> str:
    """添加北京口癖"""
    # 随机在句子末尾加口癖
    if random.random() < 0.4:
        suffix = random.choice(BEIJING_MANNERISMS["suffix"])
        text = text + suffix
    return text
```

## 4. 新观众欢迎语（多语言）

### 按语言分类

| 观众语言 | VTuber能力 | 欢迎语 |
|---------|-----------|--------|
| 中文 | 母语 | "欢迎[username]来到直播间！" |
| 中文 | 方言区 | "欢迎[username]来阿拉直播间！" |
| 英文 | 流利 | "Welcome [username] to the stream!" |
| 英文 | 基础 | "Welcome [username]! Thank you come!" |
| 日文 | 流利 | "コメントありがとうございます、[username]さん！" |
| 日文 | 基础 | "[username]さん、ありがとう！" |
| 中英混合 | 流利 | "诶[username]来了！Welcome welcome!" |
| 方言+中文 | 流利 | "[username]欢迎来到直播间！靓仔快坐！" |

## 5. 技术实现方案

### 方案A: LLM原生（推荐）
```
优点: 最自然，能处理复杂场景
缺点: 成本较高，需要设计好prompt
```

```python
def generate_response_with_language(
    danmaku: Danmaku,
    user_profile: UserProfile,
    vtuber_profile: VTuberLanguageProfile,
) -> str:
    """
    使用LLM生成多语言回应
    """
    lang_profile = detect_language(danmaku.text)

    prompt = f"""
你是VTuber主播{name}

## 你的语言能力
- 母语: {vtuber_profile.native}
- 流利: {', '.join(vtuber_profile.fluent)}
- 方言: {vtuber_profile.regional_style or '无'}
- 语言混用: {'会' if vtuber_profile.code_switching else '不会'}

## 收到的弹幕
用户: {danmaku.user}
语言: {lang_profile.primary} {lang_profile.dialect or ''}
内容: "{danmaku.text}"

## 回应要求
1. **匹配观众语言** - 用观众的语言或方言回应
2. **体现你的语言特色** - 如果会方言，适当加入方言词
3. **新观众用欢迎语** - 第一次出现用"欢迎[用户名]"
4. **熟人自然反应** - 用熟悉的语气

## 方言示例
上海话: "伐", "噶", "阿拉", "嗲"
粤语: "架", "靓仔", "真系", "冇问题"

## 回应示例
观众"小明"(新)发"哈哈哈哈": "欢迎小明来到直播间！"
观众"小红"(上海话，老观众)发"好笑": "小红你来了伐，真的好笑噶"
观众"John"(新)发"lol": "Welcome John to the stream!"

生成回应:
"""

    response = llm.call(prompt, max_tokens=200)
    return response
```

### 方案B: 规则+LLM混合
```
优点: 成本低，可控
缺点: 不如LLM灵活
```

```python
def generate_response_hybrid(
    danmaku: Danmaku,
    user_profile: UserProfile,
    vtuber_profile: VTuberLanguageProfile,
) -> str:
    """混合方案"""
    lang = detect_language(danmaku.text)

    # 1. 新观众欢迎语（模板）
    if user_profile.interaction_count == 0:
        return get_welcome_message(
            username=danmaku.user,
            language=lang.primary,
            vtuber_profile=vtuber_profile
        )

    # 2. 熟人用LLM生成（带语言上下文）
    language_context = build_language_context(lang, vtuber_profile)

    response = llm.call(f"""
根据用户语言和你的语言特色生成回应:
- 用户语言: {lang.primary}
- 你的方言: {vtuber_profile.regional_style}
- 你的口癖: {vtuber_profile.catchphrases}
- 弹幕: {danmaku.text}

回应要{language_context}
""")

    return response
```

## 6. 数据结构设计

### 语言档案
```python
@dataclass
class LanguageProfile:
    primary: str              # "zh" | "en" | "ja" | "mixed"
    secondary: Optional[str]  # "zh" | "en" | "ja"
    dialect: Optional[str]    # "shanghai" | "cantonese"
    confidence: float = 1.0

    def to_context(self) -> str:
        """生成LLM上下文"""
        parts = [self.primary]
        if self.secondary:
            parts.append(self.secondary)
        if self.dialect:
            parts.append(self.dialect)
        return "+".join(parts)
```

### 方言词典
```python
REGIONAL_DICTS = {
    "shanghai": {
        "是伐": "是吧",
        "噶": "的",
        "阿拉": "我们",
        "嗲": "可爱/撒娇",
        "勿要": "不要",
    },
    "cantonese": {
        "架": "的/强调",
        "靓仔": "帅哥",
        "真系": "真是",
        "冇问题": "没问题",
        "好犀利": "好厉害",
    },
    "beijing": {
        "您": "你",
        "咱": "我们",
        "倍儿": "特别",
        "这": "这个",
    },
}
```

## 7. 推荐实现步骤

### Phase 1: 基础检测
1. 实现语言检测函数
2. 支持中文、英文、日文检测
3. 检测混合语言

### Phase 2: VTuber语言配置
1. 创建 `VTuberLanguageProfile` 数据类
2. 在 engine setup 时传入语言配置
3. 提供预设配置（上海话、粤语、国际）

### Phase 3: 多语言回应
1. 新观众欢迎语（按语言）
2. 基于语言配置的LLM prompt
3. 方言词/口癖注入

### Phase 4: 高级特性
1. 中英夹杂自然度
2. 方言程度可调
3. 学习观众语言偏好

## 8. 使用示例

### 配置VTuber语言
```python
from echuu.live.engine import EchuuLiveEngine
from echuu.live.language import VTuberLanguageProfile

# 创建上海话VTuber
lang_profile = VTuberLanguageProfile(
    native="zh-CN",
    fluent=["en-US"],
    basic=["zh-shanghai"],
    regional_style="上海话",
    accent_level=0.7,
    code_switching=True,
    code_switching_rate=0.3,
)

engine = EchuuLiveEngine()
engine.setup(
    name="六螺",
    persona="25岁上海女主播，活泼爱吐槽",
    topic="第一次直播的紧张经历",
    background="刚辞职做全职主播",
    language_profile=lang_profile,  # 新增
)

# 观众发弹幕
danmaku = Danmaku(text="好好笑", user="小明")

# 自动生成: "小明你来了伐，真的好笑噶"
response = engine.handle_danmaku(danmaku)
```

### 预设配置示例
```python
# 国际VTuber
international = VTuberLanguageProfile.international(
    fluent=["zh-CN", "en-US", "ja-JP"]
)

# 香港VTuber
hongkong = VTuberLanguageProfile.cantonese(
    fluent=["zh-CN", "en-US", "yue-HK"],
    accent_level=0.6
)

# 上海VTuber
shanghai = VTuberLanguageProfile.shanghai(
    fluent=["zh-CN", "en-US"],
    accent_level=0.7
)
```

这个方案如何？我可以先实现基础版本（语言检测+欢迎语+基础方言支持），然后逐步添加高级特性。
