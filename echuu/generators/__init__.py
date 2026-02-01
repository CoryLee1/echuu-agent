"""
Generators for Echuu - script and content generation.

This module contains:
- ScriptGeneratorV4: Main 4-phase script generation pipeline
- ScriptGeneratorV4_1: Enhanced version with story nucleus
- ScriptLineV4: Data structure for script lines
- ExampleSampler: Few-shot learning from real clips
"""

from .script_generator_v4 import ScriptGeneratorV4, ScriptGeneratorV4_1, ScriptLineV4
from .example_sampler import ExampleSampler

__all__ = [
    "ScriptGeneratorV4",
    "ScriptGeneratorV4_1",
    "ScriptLineV4",
    "ExampleSampler",
]
