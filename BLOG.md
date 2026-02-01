# Echuu: Building an AI That Talks Like a Real Streamer

## The Problem with AI Streamers

Most AI streamers sound robotic. They deliver polished, well-structured monologues that feel more like news broadcasts than casual conversations. Real streamers don't talk like that. They:

- Start a story, get distracted, and never finish it
- Express contradictory emotions in the same breath
- Respond to chat mid-sentence
- Forget what they were saying
- Tell stories because something random triggered a memory

**Echuu** is an attempt to capture this messy, human spontaneity.

## What is Echuu?

Echuu is an AI VTuber auto-live system that learns from real streamer clips and generates natural, interactive broadcast content. Instead of writing formal scripts, it recreates the **cognitive patterns** of how humans spontaneously share stories.

The name "echuu" (エチュウ) evokes the idea of an etude - a practice piece that captures the essence of natural expression.

## Core Philosophy: Imperfection as a Feature

Traditional AI generates polished content. Echuu deliberately breaks this:

### 1. Story Nucleus System

Every story begins with a "nucleus" - the core reason someone wants to share something. Echuu identifies:

- **Sharing Urge**: Why tell this story NOW? (Need validation? Want to complain? Showing off?)
- **Abnormality**: What makes it interesting? (Plot twist? Embarrassing moment? Moral dilemma?)
- **Pattern**: What narrative structure fits? (Slippery slope? Contradiction reveal? Tiny shame?)

### 2. Emotion Mixing

Real emotions are messy. Echuu models:

- **Masked Emotions**: Love expressed as annoyance, anxiety hidden behind humor
- **Emotional Contradictions**: Feeling grateful AND resentful simultaneously
- **Surface vs. Deep**: What you say vs. what you actually feel

### 3. Structure Breaking

After generating a script, Echuu deliberately "breaks" it:

- Removes neat conclusions ("And that's when I learned...")
- Adds realistic endings ("Wait, what was I saying?", "Oh, commercial break!")
- Injects tangents at random points
- Ensures the narrative feels unscripted

## How It Works

### Phase -1: Story Nucleus Generation
The system selects from 6 core narrative patterns:
- **Slippery Slope**: Small compromises snowball into chaos
- **Contradiction Reveal**: Hidden persona vs. reality exposed
- **Kindness Trap**: Unexpected kindness triggers complex feelings
- **Anger Armor**: Anger masks vulnerability
- **Tiny Shame**: Embarrassing moments told for laughs
- **Choice Cost**: Hard decisions with unspoken consequences

### Phase 0: Trigger Selection
How does the story start? Real streamers don't say "Today I'll tell you about X." They get triggered by:
- **Sensory cues**: "This song reminds me of..."
- **Chat messages**: "Someone asked about my worst date..."
- **Random thoughts**: "Actually wait, this reminds me..."
- **Environment**: "Is it raining? That reminds me of when..."

### Phase 1: Build Immersion
Establish the character's psychological state and emotional baseline.

### Phase 2: Script Generation
Claude LLM generates 8-10 narrative units, each with:
- Text content (80-120 words)
- Stage (Hook/Build-up/Climax/Resolution)
- Interruption cost (how bad is it to interrupt here?)
- Key information markers

### Phase 3: Structure Breaking
Deliberately imperfect the output:
- Remove sublimation endings
- Add non-closure endings
- Insert realistic digressions

## Real-Time Performance

Once the script is generated, **PerformerV3** executes it step by step:

```
For each script line:
1. Check incoming chat (danmaku)
2. Calculate: Should I respond or continue?
   - decision_value = relevance - interruption_cost
   - If positive: respond to chat
   - If negative: continue script
3. Update memory (promises made, story points, emotions)
4. Generate TTS audio
5. Broadcast to frontend
```

### Memory System

The AI remembers:
- **Promises**: "I'll tell you about that later" - tracked for fulfillment
- **Story Points**: What's been revealed vs. upcoming
- **Chat History**: Which messages were addressed
- **Emotional State**: Current intensity and trajectory

## The Tech Stack

### Backend (Python)
- **LLM**: Anthropic Claude for script generation and responses
- **TTS**: Qwen3 Realtime (Alibaba) for natural Chinese speech
- **Web**: FastAPI + WebSocket for real-time streaming
- **State**: Custom memory system for coherent interactions

### Frontend (React)
- **Framework**: React 19 + Vite + TypeScript
- **Styling**: Tailwind CSS
- **Real-time**: WebSocket for live updates
- **Audio**: Auto-playback of TTS output

## Architecture Overview

```
User Input (Topic + Character)
        ↓
┌───────────────────────────────────┐
│      Script Generation Pipeline   │
├───────────────────────────────────┤
│ Phase -1: Story Nucleus           │
│ Phase  0: Trigger Selection       │
│ Phase  1: Immersion Building      │
│ Phase  2: LLM Script Generation   │
│ Phase  3: Structure Breaking      │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│      Real-time Performer          │
├───────────────────────────────────┤
│ • Execute script step by step     │
│ • Handle chat interruptions       │
│ • Update memory state             │
│ • Generate TTS audio              │
│ • Broadcast via WebSocket         │
└───────────────────────────────────┘
        ↓
    Frontend Display
    (Live monitoring, audio playback)
```

## Example Output

Input:
- Character: "Liu Luo" (六螺), a quirky female streamer
- Topic: "Gossip about my boss"

The system might generate:

> "Wait, why did I suddenly think of this... Oh right, that chat message. Someone asked about workplace drama? Okay so my boss, right..."
>
> [interruption cost: 2]
>
> "He has this THING where he pretends to be super chill but then passive-aggressively comments on your work... like 'Oh interesting choice with that font' and you KNOW he hates it..."
>
> [interruption cost: 5 - climax, don't interrupt]
>
> "Anyway someone's asking about - oh wait I didn't finish the story. Or did I? Actually the point was... hmm... OH the font thing led to this whole..."

Notice:
- Natural trigger ("why did I suddenly think of this")
- Self-interruption ("Oh right, that chat message")
- Emotional intensity in caps ("THING", "KNOW")
- Non-closure ending ("actually the point was... hmm")

## Why This Matters

As AI content generation becomes ubiquitous, the difference between "AI content" and "human content" is increasingly about **imperfection patterns**.

Humans:
- Lose track of their point
- Express contradictory emotions
- Get distracted by tangents
- Tell stories because of random triggers
- Have linguistic quirks and habits

Echuu attempts to model these patterns, not just generate grammatically correct scripts. The goal isn't to fool anyone into thinking it's human - it's to create content that **feels** more human, more engaging, more real.

## Try It Yourself

```bash
# Clone and install
git clone https://github.com/your-repo/echuu-agent
cd echuu-agent
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your Anthropic and Dashscope keys

# Run interactive mode
python workflow/backend/echuu_interactive.py

# Or start the web interface
cd echuu-web/backend && python main.py
cd echuu-web/frontend && npm run dev
```

## What's Next

The `echuu-web` subfolder is an ongoing effort to:
1. Move the core engine into a proper backend service
2. Build a React dashboard for real-time monitoring
3. Enable character management and session history
4. Support live danmaku injection

The frontend is currently informal and being reorganized with shadcn/ui components for a more polished experience.

---

*Echuu is an open experiment in making AI feel less artificial. The code is messy, the philosophy is ambitious, and the results are... interestingly imperfect. Just like real streamers.*
