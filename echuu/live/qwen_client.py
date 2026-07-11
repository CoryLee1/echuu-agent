"""
LLM 客户端封装（Qwen / DashScope OpenAI 兼容模式）。
"""

from __future__ import annotations

import os
from typing import Optional

# 华北2（北京）地域；新加坡地域为 dashscope-intl.aliyuncs.com
_CN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_INTL_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


class QwenClient:
    """Qwen LLM 客户端（DashScope OpenAI 兼容模式）。"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model or os.getenv("QWEN_MODEL", "qwen-plus")
        self.client = None

        if not self.api_key:
            raise ValueError("未设置 DASHSCOPE_API_KEY，无法使用 Qwen")

        region = os.getenv("QWEN_REGION", "cn").lower()
        base_url = _INTL_BASE_URL if region in ("sg", "intl", "international") else _CN_BASE_URL

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key, base_url=base_url)
            print(f"LLM 已初始化: {self.model} (DashScope)")
        except ImportError:
            raise ImportError("openai 未安装，请先安装 openai>=1.52.0")

    def call(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1000) -> str:
        """调用 LLM。"""
        if not self.client:
            raise RuntimeError("LLM 未初始化，无法调用")
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"LLM 调用失败: {exc}") from exc

    def call_with_search(self, prompt: str, system: Optional[str] = None, max_tokens: int = 800) -> str:
        """带联网搜索的调用（DashScope enable_search，qwen-plus 支持）。

        用于主题语义 grounding：网络流行语（如"云养猫"）按实际用法而非字面理解。
        """
        if not self.client:
            raise RuntimeError("LLM 未初始化，无法调用")
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                extra_body={
                    "enable_search": True,
                    "search_options": {"forced_search": True},
                },
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"LLM 联网调用失败: {exc}") from exc
