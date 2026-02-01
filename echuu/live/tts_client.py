"""
TTS 客户端封装（基于 CosyVoiceTTS）。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Optional


class TTSClient:
    """轻量 TTS 包装器，提供统一接口。"""

    def __init__(self):
        self.enabled = False
        self._recording = False
        self._recording_buffer = []
        self.tts = None

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            print("未设置 DASHSCOPE_API_KEY，TTS 已禁用")
            return

        try:
            cosyvoice_cls = self._load_cosyvoice_class()
            if not cosyvoice_cls:
                raise ImportError("无法加载 CosyVoiceTTS")

            self.tts = cosyvoice_cls(
                api_key=api_key,
                model=os.getenv("TTS_MODEL"),
                voice=os.getenv("TTS_VOICE"),
            )
            self.enabled = True
            print("TTS 已启用")
        except Exception as exc:
            print(f"TTS 初始化失败: {exc}")

    @staticmethod
    def _find_project_root() -> Path:
        """寻找项目根目录（包含 .git 或 requirements.txt）。"""
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "requirements.txt").exists():
                return parent
        return Path.cwd()

    def _load_cosyvoice_class(self):
        """
        动态加载 workflow/backend/tts_client.py 中的 CosyVoiceTTS。
        """
        project_root = self._find_project_root()
        module_path = project_root / "workflow" / "backend" / "tts_client.py"
        if not module_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("workflow_backend_tts_client", module_path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "CosyVoiceTTS", None)

    def synthesize(self, text: str, emotion_boost: float = 0.0) -> Optional[bytes]:
        """
        合成语音。

        Args:
            text: 合成文本
            emotion_boost: 情绪增强参数（保留接口，不影响当前实现）
        """
        if not self.enabled or not self.tts:
            return None

        try:
            audio = self.tts.synthesize(text)
        except Exception as exc:
            print(f"[TTS] 合成错误: {exc}")
            return None

        if self._recording and audio:
            self._recording_buffer.append(audio)

        return audio

    def start_recording(self):
        """开始录制音频片段。"""
        self._recording = True
        self._recording_buffer = []

    def save_recording(self, path: str):
        """
        保存录制音频。
        
        注意：音频数据已经是正确格式（PCM已转换为WAV），直接拼接保存即可。
        """
        if not self._recording_buffer:
            print("没有可保存的录制音频")
            return

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with output_path.open("wb") as f:
                for chunk in self._recording_buffer:
                    f.write(chunk)
            file_size = sum(len(chunk) for chunk in self._recording_buffer)
            print(f"录制音频已保存: {output_path} ({file_size} bytes)")
        except Exception as exc:
            print(f"[TTS] 保存录制失败: {exc}")
        finally:
            self._recording = False
