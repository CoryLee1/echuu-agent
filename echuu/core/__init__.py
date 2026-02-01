"""
Core components for Echuu - pattern analysis and content generation.

This module contains the fundamental building blocks:
- StoryNucleus: 6 core narrative patterns
- EmotionMixer: Emotional complexity modeling
- TriggerBank: Story opening triggers
- DigressionDB: Realistic tangent injection
- StructureBreaker: Anti-perfection algorithms
- PatternAnalyzer: Learn from real clips
- DramaAmplifier: Emotional intensity control
"""

from .story_nucleus import StoryNucleus
from .emotion_mixer import EmotionMixer, EmotionConfig
from .trigger_bank import TriggerBank, TriggerTemplate
from .digression_db import DigressionDB
from .structure_breaker import StructureBreaker
from .pattern_analyzer import PatternAnalyzer
from .drama_amplifier import DramaAmplifier

__all__ = [
    "StoryNucleus",
    "EmotionMixer",
    "EmotionConfig",
    "TriggerBank",
    "TriggerTemplate",
    "DigressionDB",
    "StructureBreaker",
    "PatternAnalyzer",
    "DramaAmplifier",
]
