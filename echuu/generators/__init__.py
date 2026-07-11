"""
Generators for Echuu - script and content generation.

This module contains:
- ScriptWriter: 综艺编剧 — authors the show from RichPersona + StoryCore + few-shot
- ExampleSampler: Few-shot learning from real clips (relevance-sampled)
"""

from .script_writer import ScriptWriter
from .example_sampler import ExampleSampler

__all__ = [
    "ScriptWriter",
    "ExampleSampler",
]
