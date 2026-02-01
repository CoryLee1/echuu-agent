"""
Echuu - AI VTuber Auto-Live System

A library for generating natural, spontaneous-feeling live broadcast content
by learning from real streamer patterns.

Example usage:
    from echuu import EchuuLiveEngine

    engine = EchuuLiveEngine()
    engine.setup(
        name="六螺",
        persona="爱吐槽的女主播",
        topic="关于上司的八卦",
        background="前上班族，现全职主播"
    )

    for step in engine.run_sync():
        print(step)
"""

__version__ = "0.1.0"

# Main engine - the primary entry point
from .live.engine import EchuuLiveEngine

# Core components for customization
from .core.story_nucleus import StoryNucleus
from .core.emotion_mixer import EmotionMixer, EmotionConfig
from .core.trigger_bank import TriggerBank, TriggerTemplate
from .core.digression_db import DigressionDB
from .core.structure_breaker import StructureBreaker
from .core.pattern_analyzer import PatternAnalyzer
from .core.drama_amplifier import DramaAmplifier

# Generators
from .generators.script_generator_v4 import ScriptGeneratorV4, ScriptGeneratorV4_1, ScriptLineV4
from .generators.example_sampler import ExampleSampler

# Live performance components
from .live.state import Danmaku, PerformerMemory, PerformanceState
from .live.performer import PerformerV3
from .live.llm_client import LLMClient
from .live.tts_client import TTSClient
from .live.danmaku import DanmakuHandler, DanmakuEvaluator
from .live.response_generator import DanmakuResponseGenerator

__all__ = [
    # Version
    "__version__",
    # Main engine
    "EchuuLiveEngine",
    # Core
    "StoryNucleus",
    "EmotionMixer",
    "EmotionConfig",
    "TriggerBank",
    "TriggerTemplate",
    "DigressionDB",
    "StructureBreaker",
    "PatternAnalyzer",
    "DramaAmplifier",
    # Generators
    "ScriptGeneratorV4",
    "ScriptGeneratorV4_1",
    "ScriptLineV4",
    "ExampleSampler",
    # Live
    "Danmaku",
    "PerformerMemory",
    "PerformanceState",
    "PerformerV3",
    "LLMClient",
    "TTSClient",
    "DanmakuHandler",
    "DanmakuEvaluator",
    "DanmakuResponseGenerator",
]
