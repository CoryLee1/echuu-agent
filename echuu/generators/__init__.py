"""
Generators for Echuu - script and content generation.

This module contains:
- ScriptGeneratorV5: Unit-based single-call script generation (current)
- ExampleSampler: Few-shot learning from real clips
"""

from .script_generator_v5 import ScriptGeneratorV5
from .example_sampler import ExampleSampler

__all__ = [
    "ScriptGeneratorV5",
    "ExampleSampler",
]
