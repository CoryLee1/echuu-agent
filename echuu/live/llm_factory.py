"""
LLM Factory - 动态选择 LLM 提供商。
Supports Gemini 3, Claude, and OpenAI.
"""

from __future__ import annotations

import os
from typing import Optional, Protocol


class LLMClientProtocol(Protocol):
    """LLM 客户端协议（接口）。"""

    def call(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1000) -> str:
        ...


def create_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    thinking_level: Optional[str] = None,
) -> LLMClientProtocol:
    """
    创建 LLM 客户端。

    Args:
        provider: LLM 提供商 ("claude", "gemini", "openai")。
                  如果未指定，根据可用的 API Key 自动选择。
        api_key: API 密钥（可选，默认从环境变量读取）。
        model: 模型名称（可选，默认使用提供商默认模型）。
        thinking_level: Gemini 3 思考级别 ("low", "medium", "high", "minimal")。

    Returns:
        LLM 客户端实例。

    Provider 优先级（自动选择时）:
        1. Gemini (如果 GEMINI_API_KEY 存在)
        2. Claude (如果 ANTHROPIC_API_KEY 存在)
        3. OpenAI (如果 OPENAI_API_KEY 存在)

    Gemini 3 Models:
        - gemini-3-pro-preview: Most intelligent, complex reasoning
        - gemini-3-flash-preview: Fast, high-intelligence, cost-effective
        - gemini-3-pro-image-preview: High-quality image generation
    """
    # 如果指定了 provider，直接使用
    if provider:
        provider = provider.lower()
        if provider in ("gemini", "google"):
            from .gemini_client import GeminiClient

            # Default to Gemini 3 Flash if no model specified
            if model is None:
                model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

            return GeminiClient(api_key=api_key, model=model, thinking_level=thinking_level)
        elif provider in ("claude", "anthropic"):
            from .llm_client import LLMClient
            return LLMClient(api_key=api_key, model=model)
        elif provider == "openai":
            raise NotImplementedError("OpenAI client not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    # 自动选择：根据可用的 API Key
    if os.getenv("GEMINI_API_KEY"):
        from .gemini_client import GeminiClient

        if model is None:
            model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

        return GeminiClient(api_key=api_key, model=model, thinking_level=thinking_level)

    if os.getenv("ANTHROPIC_API_KEY"):
        from .llm_client import LLMClient
        return LLMClient(api_key=api_key, model=model)

    if os.getenv("OPENAI_API_KEY"):
        raise NotImplementedError("OpenAI client not yet implemented")

    raise ValueError(
        "未找到可用的 LLM API Key。请设置以下环境变量之一：\n"
        "  - GEMINI_API_KEY (Google Gemini)\n"
        "  - ANTHROPIC_API_KEY (Anthropic Claude)\n"
        "  - OPENAI_API_KEY (OpenAI)"
    )
