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

### 3. 运行数据标注

```bash
# 快速模式（不需要API Key，使用启发式规则）
python workflow/data-annotation-process/run_annotation.py --quick

# LLM精细标注（需要配置API Key）
python workflow/data-annotation-process/run_annotation.py
```

### 4. 使用标注数据

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
```

## 核心概念### 标注维度| 维度 | 说明 | 取值 |
|------|------|------|
| attention_focus | 注意力指向 | self, audience, specific, content, meta |
| speech_act | 话语行为 | narrate, opine, respond, elicit, pivot, backchannel |
| trigger | 触发源 | sc, danmaku, self, content, prior |

### Interruption Costechuu 的核心机制：决定是否响应弹幕的动态代价

```python
decision_value = urgency - cost
# 正数 → 回应弹幕
# 负数 → 继续剧本
```

### Inner Monologue

让观众看到AI的"思考过程"，这是 echuu 区别于传统AI主播的核心特性

## 数据格式

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
```

### 标注数据 (JSON)```json
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
python workflow/data-annotation-process/run_annotation.py --quick

# 只标注部分数据（测试用）
python workflow/data-annotation-process/run_annotation.py --max-clips 5

# 检查配置
python workflow/data-annotation-process/run_annotation.py --dry-run

# 指定输出路径
python workflow/data-annotation-process/run_annotation.py -o custom_output.json
```

## 许可证

MIT License
