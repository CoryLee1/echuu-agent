# Echuu-Agent: Complete Reconstruction Guide

This document provides a comprehensive guide to understanding, setting up, and reconstructing the entire echuu-agent project.

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Directory Structure](#directory-structure)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the Project](#running-the-project)
8. [Core Components Deep Dive](#core-components-deep-dive)
9. [Web Interface (echuu-web)](#web-interface-echuu-web)
10. [Data Pipeline](#data-pipeline)
11. [API Reference](#api-reference)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

**Echuu-agent** is an AI VTuber (Virtual Streamer) auto-live system that:

- Learns performance patterns from real streamer clips
- Generates natural, spontaneous-feeling live broadcast content
- Handles real-time chat (danmaku) interactions
- Synthesizes speech using TTS (Text-to-Speech)
- Provides a web dashboard for monitoring and control

### Key Innovations

1. **Story Nucleus System**: 6 core narrative patterns that drive storytelling
2. **Emotion Mixing**: Models complex, contradictory emotions
3. **Structure Breaking**: Deliberately imperfects AI output for realism
4. **Interruption Cost**: Dynamic decision-making for chat responses
5. **Memory System**: Maintains coherent state across interactions

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        echuu-agent                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Core Engine (echuu/)                   │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │    core/    │  │ generators/ │  │      live/      │   │  │
│  │  ├─────────────┤  ├─────────────┤  ├─────────────────┤   │  │
│  │  │story_nucleus│  │script_gen_v4│  │     engine      │   │  │
│  │  │emotion_mixer│  │example_sampl│  │    performer    │   │  │
│  │  │trigger_bank │  └─────────────┘  │   llm_client    │   │  │
│  │  │digression_db│                   │   tts_client    │   │  │
│  │  │struct_break │                   │     state       │   │  │
│  │  └─────────────┘                   └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Web Layer (echuu-web/)                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  ┌─────────────────┐       ┌─────────────────────────┐   │  │
│  │  │    Backend      │◄─────►│       Frontend          │   │  │
│  │  │    (FastAPI)    │  WS   │       (React)           │   │  │
│  │  ├─────────────────┤       ├─────────────────────────┤   │  │
│  │  │ REST API        │       │ LiveMonitor.tsx         │   │  │
│  │  │ WebSocket       │       │ Characters.tsx          │   │  │
│  │  │ Live Service    │       │ History.tsx             │   │  │
│  │  └─────────────────┘       └─────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
echuu-agent/
├── echuu/                          # Core AI engine
│   ├── __init__.py
│   ├── core/                       # Pattern analysis & generation
│   │   ├── __init__.py
│   │   ├── story_nucleus.py        # 6 narrative patterns
│   │   ├── emotion_mixer.py        # Emotional complexity
│   │   ├── trigger_bank.py         # Story opening triggers
│   │   ├── digression_db.py        # Realistic tangents
│   │   ├── structure_breaker.py    # Anti-perfection algorithms
│   │   ├── pattern_analyzer.py     # Learn from clips
│   │   └── drama_amplifier.py      # Emotional intensity
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── script_generator_v4.py  # 4-phase generation pipeline
│   │   └── example_sampler.py      # Few-shot learning
│   └── live/
│       ├── __init__.py
│       ├── engine.py               # Main EchuuLiveEngine
│       ├── state.py                # Runtime state & memory
│       ├── performer.py            # Real-time execution
│       ├── llm_client.py           # Claude API wrapper
│       ├── tts_client.py           # Text-to-speech client
│       ├── danmaku.py              # Chat interaction logic
│       └── response_generator.py   # Danmaku response generation
│
├── echuu-web/                      # Web interface
│   ├── backend/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── models.py               # Pydantic schemas
│   │   ├── state.py                # WebSocket state
│   │   ├── config.py               # Backend config
│   │   ├── routers/
│   │   │   ├── api.py              # REST endpoints
│   │   │   └── websocket.py        # WebSocket handler
│   │   └── services/
│   │       └── live_service.py     # Engine orchestration
│   └── frontend/
│       ├── src/
│       │   ├── pages/              # React pages
│       │   ├── components/         # UI components
│       │   ├── hooks/              # Custom hooks
│       │   ├── api/                # API client
│       │   └── App.tsx             # Router
│       ├── package.json
│       └── vite.config.ts
│
├── workflow/                       # CLI tools & pipelines
│   ├── backend/
│   │   ├── echuu_interactive.py    # Interactive CLI
│   │   ├── echuu_demo.py           # Demo script
│   │   ├── echuu_live_engine.py    # Engine wrapper
│   │   └── tts_client.py           # TTS implementation
│   ├── data-annotation-process/    # Data labeling
│   │   ├── data_annotation_pipeline.py
│   │   └── run_annotation.py
│   └── jupyter_notebook/           # Notebooks
│
├── data/                           # Training data
│   ├── vtuber_raw_clips_*.jsonl    # Raw streamer clips
│   └── annotated_clips.json        # Labeled data
│
├── output/                         # Generated content
│   └── scripts/                    # Scripts + audio files
│
├── docs/
│   └── qwen_tts_voices.md          # TTS voice reference
│
├── .env.example                    # Environment template
├── requirements.txt                # Python dependencies
├── README.md                       # Original README
├── README_RECONSTRUCTION.md        # This file
└── BLOG.md                         # Project introduction
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| npm | 9+ | Package management |
| Git | 2.0+ | Version control |

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| Anthropic Claude | LLM for script generation | [console.anthropic.com](https://console.anthropic.com) |
| Alibaba Dashscope | Qwen TTS for speech | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/?tab=model#/api-key) |

### Optional

| Service | Purpose |
|---------|---------|
| OpenAI | Alternative LLM |

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-repo/echuu-agent.git
cd echuu-agent
```

### Step 2: Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Frontend Setup

```bash
cd echuu-web/frontend
npm install
cd ../..
```

### Step 4: Verify Installation

```bash
# Check Python packages
python -c "import anthropic; import dashscope; import fastapi; print('OK')"

# Check Node packages
cd echuu-web/frontend && npm list react && cd ../..
```

---

## Configuration

### Step 1: Create Environment File

```bash
cp .env.example .env
```

### Step 2: Edit .env

```bash
# Required: LLM API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Required: TTS API
DASHSCOPE_API_KEY=sk-xxxxx

# TTS Settings (defaults work well)
TTS_MODEL=qwen3-tts-flash-realtime
TTS_VOICE=Cherry
TTS_REGION=cn

# LLM Model Selection
DEFAULT_MODEL=claude-sonnet-4-20250514
```

### Step 3: Available TTS Voices

See `docs/qwen_tts_voices.md` for full list. Common voices:

| Voice | Gender | Style |
|-------|--------|-------|
| Cherry | Female | Warm, natural |
| Serena | Female | Professional |
| Ethan | Male | Warm |
| Chelsie | Female | Gentle |

---

## Running the Project

### Option 1: Interactive CLI (Simplest)

```bash
python workflow/backend/echuu_interactive.py
```

Interactive prompts:
1. Enter character name (e.g., "六螺")
2. Enter character persona
3. Enter character background
4. Choose topic mode (custom/preset/hybrid)
5. Watch generation and performance

Output saved to `output/scripts/`

### Option 2: Web Interface (Full Features)

**Terminal 1 - Backend:**
```bash
cd echuu-web/backend
python main.py
# Runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd echuu-web/frontend
npm run dev
# Runs on http://localhost:5173
```

**Usage:**
1. Open http://localhost:5173
2. Go to "Characters" → Create character
3. Go to "Live Monitor" → Enter topic → Start
4. Watch real-time generation
5. Audio auto-plays if enabled
6. Inject danmaku (chat) to test interactions

### Option 3: Data Annotation

```bash
# Quick mode (no API needed)
python workflow/data-annotation-process/run_annotation.py --quick

# Full LLM annotation
python workflow/data-annotation-process/run_annotation.py
```

---

## Core Components Deep Dive

### 1. Script Generation Pipeline

Located: `echuu/generators/script_generator_v4.py`

```python
# 4-Phase Pipeline
Phase -1: Story Nucleus → Select pattern, sharing_urge, abnormality
Phase  0: Trigger      → Select opening style (sensory, danmaku, etc.)
Phase  1: Immersion    → Build psychological state
Phase  2: Generation   → Claude LLM generates script (8-10 units)
Phase  3: Breaking     → Deliberately imperfect the output
```

### 2. Story Nucleus Patterns

Located: `echuu/core/story_nucleus.py`

| Pattern | Chinese | Description |
|---------|---------|-------------|
| slippery_slope | 心理滑坡 | Small compromises snowball |
| contradiction_reveal | 反差暴露 | Hidden contradiction exposed |
| kindness_trap | 善意困境 | Kindness triggers complex emotions |
| anger_armor | 愤怒掩护 | Anger masks vulnerability |
| tiny_shame | 微小羞耻 | Embarrassing moments for laughs |
| choice_cost | 选择代价 | Hard choices with hidden costs |

### 3. Emotion Mixer

Located: `echuu/core/emotion_mixer.py`

Models emotional masking:
```python
# Surface emotion ≠ Real emotion
masks = {
    "vulnerability_as_anger": "Shut up" → "I'm hurt",
    "gratitude_as_complaint": "Ugh, again" → "Thank you",
    "anxiety_as_humor": Jokes → Nervousness
}
```

### 4. Live Performance Engine

Located: `echuu/live/engine.py`

```python
class EchuuLiveEngine:
    def generate_script(topic, character):
        # Run 4-phase pipeline

    async def perform():
        # Execute each script line
        # Handle danmaku interruptions
        # Generate TTS audio
        # Update memory state
```

### 5. Interruption Cost System

```python
decision_value = (danmaku.relevance * bonus) - (line.cost * penalty)

if decision_value > 0:
    respond_to_danmaku()  # Chat is important
else:
    continue_script()      # Story is at critical point
```

### 6. Memory System

Located: `echuu/live/state.py`

```python
class PerformerMemory:
    script_progress    # Current line, stage, total
    danmaku_history    # Received, responded, pending
    story_points       # Mentioned, upcoming, revealed
    promises           # "I'll tell you later" tracking
    emotion_track      # Current intensity, trajectory
```

---

## Web Interface (echuu-web)

### Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/start` | POST | Start live session |
| `/api/history` | GET | List past sessions |
| `/api/download/{id}` | GET | Download session files |
| `/api/danmaku` | POST | Inject chat message |
| `/ws` | WebSocket | Real-time updates |

### WebSocket Messages

```json
// Reasoning phase
{"type": "reasoning", "message": "Phase -1: Determining story nucleus..."}

// Script ready
{"type": "ready", "script": [...]}

// Step execution
{
  "type": "step",
  "text": "Current speech text",
  "stage": "climax",
  "action": "script|danmaku_response",
  "audio_url": "/audio/xxx.mp3",
  "memory": {...}
}

// Session complete
{"type": "complete", "session_id": "xxx"}
```

### Frontend Pages

| Page | Path | Purpose |
|------|------|---------|
| Overview | `/` | Dashboard, recent sessions |
| Characters | `/characters` | Create/edit VTuber personas |
| Live Monitor | `/live` | Real-time streaming control |
| History | `/history` | Session archive, downloads |
| Settings | `/settings` | Configuration |

### Current State of echuu-web

The frontend is functional but informal:

**Completed:**
- Basic routing and layout
- WebSocket connection for real-time updates
- Character CRUD operations
- Live streaming with audio playback
- Session history and download

**Needs Work:**
- UI organization and consistency
- Proper component structure with shadcn/ui
- State management refinement
- Mobile responsiveness
- Error handling UX

---

## Data Pipeline

### Raw Data Format (JSONL)

```json
{
  "clip_id": "clip_001",
  "source": "StreamerName",
  "language": "zh",
  "duration": 180,
  "title": "Clip Title",
  "notes": {
    "trigger": "Danmaku about work",
    "habit": "Says 'right?' often",
    "structure": "Empathy→Experience→Comparison→Advice"
  },
  "transcript": [
    {"t": 0, "text": "Opening line..."},
    {"t": 5, "text": "Next segment..."}
  ]
}
```

### Annotated Data Format (JSON)

```json
{
  "clip_id": "clip_001",
  "skeleton": "empathy→self_experience→comparison→advice→sublimation",
  "catchphrases": ["right?", "I think"],
  "segments": [
    {
      "id": "seg_01",
      "start_time": 0,
      "end_time": 35,
      "text": "Segment text...",
      "attention_focus": "self",
      "speech_act": "opine",
      "trigger": "danmaku"
    }
  ]
}
```

### Annotation Dimensions

| Dimension | Values | Description |
|-----------|--------|-------------|
| attention_focus | self, audience, specific, content, meta | Where attention is directed |
| speech_act | narrate, opine, respond, elicit, pivot, backchannel | Type of speech |
| trigger | sc, danmaku, self, content, prior | What triggered this segment |

---

## API Reference

### EchuuLiveEngine

```python
from echuu.live.engine import EchuuLiveEngine

engine = EchuuLiveEngine(
    character_name="六螺",
    persona="Quirky female streamer who loves cats",
    background="Former office worker turned streamer"
)

# Generate script
script = await engine.generate_script(topic="关于上司的八卦")

# Perform (execute script with TTS)
async for event in engine.perform():
    print(event)
```

### TTSClient

```python
from echuu.live.tts_client import TTSClient

client = TTSClient()
audio_path = await client.synthesize("Hello world", output_path="output.mp3")
```

### LLMClient

```python
from echuu.live.llm_client import LLMClient

client = LLMClient()
response = await client.generate(
    system_prompt="You are a helpful assistant",
    user_prompt="Tell me a story"
)
```

---

## Troubleshooting

### Common Issues

**1. API Key Errors**
```
Error: Invalid API key
```
Solution: Check `.env` file, ensure no quotes around keys

**2. TTS Connection Failed**
```
Error: WebSocket connection failed
```
Solution: Check `TTS_REGION` in `.env` (use `cn` for China, `sg` for international)

**3. Module Not Found**
```
ModuleNotFoundError: No module named 'echuu'
```
Solution: Run from project root, ensure virtual environment is activated

**4. Frontend Not Connecting**
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```
Solution: Ensure backend is running on port 8000

**5. Audio Not Playing**
```
No audio output
```
Solution: Check browser autoplay settings, ensure audio files exist in output folder

### Debug Mode

```bash
# Enable verbose logging
export VERBOSE=true
python workflow/backend/echuu_interactive.py

# Or in .env
VERBOSE=true
```

### Health Checks

```bash
# Test API connection
python -c "
import anthropic
client = anthropic.Anthropic()
print(client.models.list())
"

# Test TTS
python -c "
from echuu.live.tts_client import TTSClient
import asyncio
client = TTSClient()
asyncio.run(client.synthesize('测试', 'test.mp3'))
"
```

---

## Development

### Running Tests

```bash
# Python tests (if available)
pytest tests/

# Frontend tests
cd echuu-web/frontend
npm test
```

### Code Style

```bash
# Python
pip install black isort
black echuu/
isort echuu/

# Frontend
cd echuu-web/frontend
npm run lint
```

### Contributing

1. Create feature branch
2. Make changes
3. Test locally
4. Submit PR

---

## License

MIT License - See LICENSE file

---

## Credits

- Built with Anthropic Claude API
- TTS powered by Alibaba Qwen
- Frontend framework: React + Vite + Tailwind

---

*Last updated: January 2026*
