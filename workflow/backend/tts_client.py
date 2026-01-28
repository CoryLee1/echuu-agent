"""
通义千问 TTS Client
支持 Qwen3 实时语音合成与离线语音合成
"""

import base64
import io
import os
import threading
from datetime import datetime
from typing import Callable, List, Optional

# 尝试导入 dashscope
try:
    import dashscope

    from dashscope.audio.tts_v2 import AudioFormat as OfflineAudioFormat
    from dashscope.audio.tts_v2 import ResultCallback, SpeechSynthesizer

    try:
        from dashscope.audio.qwen_tts_realtime import AudioFormat as RealtimeAudioFormat
        from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback

        REALTIME_AVAILABLE = True
    except Exception:
        REALTIME_AVAILABLE = False
        QwenTtsRealtime = None
        QwenTtsRealtimeCallback = object
        RealtimeAudioFormat = None

    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print("⚠️ dashscope 未安装，请运行: pip install dashscope")


class TTSCallback(ResultCallback):
    """TTS 流式回调处理"""
    
    def __init__(self, 
                 on_audio: Callable[[bytes], None] = None,
                 save_path: str = None):
        self.on_audio = on_audio
        self.save_path = save_path
        self.audio_buffer = io.BytesIO()
        self.file = None
        self.first_chunk_time = None
        self.start_time = None
        
    def on_open(self):
        self.start_time = datetime.now()
        if self.save_path:
            self.file = open(self.save_path, "wb")
        print(f"[TTS] 连接建立")
    
    def on_data(self, data: bytes):
        if self.first_chunk_time is None:
            self.first_chunk_time = datetime.now()
            latency = (self.first_chunk_time - self.start_time).total_seconds() * 1000
            print(f"[TTS] 首包延迟: {latency:.0f}ms")
        
        # 写入 buffer
        self.audio_buffer.write(data)
        
        # 写入文件
        if self.file:
            self.file.write(data)
        
        # 回调处理
        if self.on_audio:
            self.on_audio(data)
    
    def on_complete(self):
        print(f"[TTS] 合成完成，音频大小: {self.audio_buffer.tell()} bytes")
    
    def on_error(self, message: str):
        print(f"[TTS] 错误: {message}")
    
    def on_close(self):
        if self.file:
            self.file.close()
        print("[TTS] 连接关闭")
    
    def on_event(self, message):
        pass
    
    def get_audio(self) -> bytes:
        """获取完整音频数据"""
        return self.audio_buffer.getvalue()


class QwenRealtimeCallback(QwenTtsRealtimeCallback):
    """Qwen3 Realtime 回调处理"""

    def __init__(self, on_audio: Callable[[bytes], None] = None, save_path: str = None):
        super().__init__()
        self.on_audio = on_audio
        self.save_path = save_path
        self.audio_buffer = io.BytesIO()
        self.file = open(save_path, "wb") if save_path else None
        self.complete_event = threading.Event()

    def on_open(self) -> None:
        print("[TTS] Realtime 连接建立")

    def on_close(self, close_status_code, close_msg) -> None:
        if self.file:
            self.file.close()
        print(f"[TTS] Realtime 连接关闭: {close_status_code}, {close_msg}")

    def on_event(self, response) -> None:
        try:
            if isinstance(response, str):
                import json
                try:
                    response = json.loads(response)
                except:
                    return
            
            event_type = response.get("type")
            # print(f"[TTS] on_event: {event_type}")
            
            if event_type == "response.audio.delta":
                recv_audio_b64 = response.get("delta")
                if recv_audio_b64:
                    chunk = base64.b64decode(recv_audio_b64)
                    self.audio_buffer.write(chunk)
                    if self.file:
                        self.file.write(chunk)
                    if self.on_audio:
                        self.on_audio(chunk)
            
            if event_type in ("response.done", "session.finished"):
                if event_type == "response.done":
                    print(f"[TTS] 收到音频分片完成: {self.audio_buffer.tell()} bytes")
                self.complete_event.set()
            
            if event_type == "error":
                print(f"[TTS] 收到错误事件: {response}")
                self.complete_event.set()
                
        except Exception as exc:
            print(f"[TTS] Realtime 回调错误: {exc}")

    def wait_for_complete(self, timeout: Optional[float] = None) -> bool:
        return self.complete_event.wait(timeout)

    def get_audio(self) -> bytes:
        return self.audio_buffer.getvalue()


class CosyVoiceTTS:
    """
    通义千问 TTS 客户端
    
    使用方法:
        tts = CosyVoiceTTS()
        audio = tts.synthesize("你好，世界！")
    """
    
    # 音频格式映射
    FORMAT_MAP = {
        "mp3": OfflineAudioFormat.MP3_22050HZ_MONO_256KBPS if DASHSCOPE_AVAILABLE else None,
        "wav": OfflineAudioFormat.WAV_22050HZ_MONO_16BIT if DASHSCOPE_AVAILABLE else None,
        "pcm": OfflineAudioFormat.PCM_22050HZ_MONO_16BIT if DASHSCOPE_AVAILABLE else None,
    }
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        voice: str = None,
        audio_format: str = "mp3",
    ):
        """
        初始化 TTS 客户端
        
        Args:
            api_key: DashScope API Key (默认从环境变量读取)
            model: TTS 模型 (默认 qwen3-tts-flash-realtime)
            voice: 音色 (默认 Cherry)
            audio_format: 音频格式 mp3/wav/pcm
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope 未安装，请运行: pip install dashscope")
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")
        
        dashscope.api_key = self.api_key
        
        self.model = model or os.getenv("TTS_MODEL", "qwen3-tts-flash-realtime")
        self.voice = voice or os.getenv("TTS_VOICE", "Cherry")
        self.audio_format = self.FORMAT_MAP.get(audio_format.lower(), self.FORMAT_MAP["mp3"])

        self.mode = os.getenv("TTS_MODE", "server_commit")
        self.language_type = os.getenv("TTS_LANGUAGE_TYPE", "Chinese")
        self.response_format = os.getenv("TTS_RESPONSE_FORMAT", "pcm")
        self.sample_rate = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
        self.speech_rate = float(os.getenv("TTS_SPEECH_RATE", "1.0"))
        self.volume = int(os.getenv("TTS_VOLUME", "50"))
        self.pitch_rate = float(os.getenv("TTS_PITCH_RATE", "1.0"))
        self.bit_rate = int(os.getenv("TTS_BIT_RATE", "128"))
        self.timeout = float(os.getenv("TTS_TIMEOUT", "60"))

        region = os.getenv("TTS_REGION", "cn").lower()
        self.ws_url = os.getenv("TTS_WS_URL")
        if not self.ws_url:
            self.ws_url = (
                "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
                if region in ("sg", "intl", "international")
                else "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
            )

        realtime = "realtime" in self.model
        if realtime and not REALTIME_AVAILABLE:
            raise ImportError("dashscope 版本过低，需 >= 1.25.2 才能使用 QwenTTS Realtime")

        print(f"✅ TTS Client 初始化: model={self.model}, voice={self.voice}, mode={self.mode}")
    
    def _is_realtime_model(self) -> bool:
        return "realtime" in self.model

    def _resolve_realtime_audio_format(self):
        if not RealtimeAudioFormat:
            return None
        fmt = self.response_format.lower()
        sample_rate = self.sample_rate
        if fmt == "pcm":
            name = f"PCM_{sample_rate}HZ_MONO_16BIT"
            return getattr(RealtimeAudioFormat, name, RealtimeAudioFormat.PCM_24000HZ_MONO_16BIT)
        if fmt == "wav":
            name = f"WAV_{sample_rate}HZ_MONO_16BIT"
            return getattr(RealtimeAudioFormat, name, RealtimeAudioFormat.PCM_24000HZ_MONO_16BIT)
        if fmt == "mp3":
            name = f"MP3_{sample_rate}HZ_MONO_128KBPS"
            return getattr(RealtimeAudioFormat, name, RealtimeAudioFormat.PCM_24000HZ_MONO_16BIT)
        if fmt == "opus":
            name = f"OPUS_{sample_rate}HZ_MONO_128KBPS"
            return getattr(RealtimeAudioFormat, name, RealtimeAudioFormat.PCM_24000HZ_MONO_16BIT)
        return RealtimeAudioFormat.PCM_24000HZ_MONO_16BIT

    def _synthesize_realtime(self, text: str, save_path: str = None) -> bytes:
        callback = QwenRealtimeCallback(save_path=save_path)
        qwen_tts_realtime = QwenTtsRealtime(
            model=self.model,
            callback=callback,
            url=self.ws_url,
        )
        qwen_tts_realtime.connect()

        response_format = self._resolve_realtime_audio_format()
        kwargs = {
            "voice": self.voice,
            "response_format": response_format,
            "mode": self.mode,
            "language_type": self.language_type,
            "speech_rate": self.speech_rate,
            "volume": self.volume,
            "pitch_rate": self.pitch_rate,
        }
        if self.response_format.lower() == "opus":
            kwargs["bit_rate"] = self.bit_rate

        qwen_tts_realtime.update_session(**kwargs)
        qwen_tts_realtime.append_text(text)
        if self.mode == "commit":
            qwen_tts_realtime.commit()
        qwen_tts_realtime.finish()

        callback.wait_for_complete(self.timeout)
        qwen_tts_realtime.close()
        return callback.get_audio()

    def _synthesize_offline(self, text: str, save_path: str = None) -> bytes:
        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format,
        )
        audio = synthesizer.call(text)
        if save_path:
            with open(save_path, "wb") as f:
                f.write(audio)
            print(f"[TTS] 音频已保存: {save_path}")
        return audio

    def synthesize(self, text: str, save_path: str = None) -> bytes:
        """
        非流式语音合成
        
        Args:
            text: 待合成文本
            save_path: 保存路径 (可选)
        
        Returns:
            音频二进制数据
        """
        if self._is_realtime_model():
            return self._synthesize_realtime(text, save_path)
        return self._synthesize_offline(text, save_path)
    
    def synthesize_streaming(self,
                            texts: List[str],
                            save_path: str = None,
                            on_audio: Callable[[bytes], None] = None) -> bytes:
        """
        双向流式语音合成
        
        Args:
            texts: 文本片段列表
            save_path: 保存路径 (可选)
            on_audio: 音频数据回调函数
        
        Returns:
            完整音频二进制数据
        """
        if self._is_realtime_model():
            joined = "".join(texts)
            return self._synthesize_realtime(joined, save_path)

        callback = TTSCallback(on_audio=on_audio, save_path=save_path)

        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format,
            callback=callback,
        )

        # 流式发送文本
        for text in texts:
            if text.strip():
                synthesizer.streaming_call(text)

        # 完成合成
        synthesizer.streaming_complete()

        return callback.get_audio()
    
    def synthesize_with_callback(self,
                                text: str,
                                save_path: str = None,
                                on_audio: Callable[[bytes], None] = None) -> bytes:
        """
        单向流式语音合成（一次性发送文本，流式接收音频）
        
        Args:
            text: 待合成文本
            save_path: 保存路径 (可选)
            on_audio: 音频数据回调函数
        
        Returns:
            完整音频二进制数据
        """
        if self._is_realtime_model():
            return self._synthesize_realtime(text, save_path)

        callback = TTSCallback(on_audio=on_audio, save_path=save_path)

        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format,
            callback=callback,
        )

        synthesizer.call(text)

        return callback.get_audio()


# ============================================
# 便捷函数
# ============================================

def text_to_speech(text: str, 
                   save_path: str = None,
                   voice: str = None,
                   model: str = None) -> bytes:
    """
    快速文本转语音
    
    Args:
        text: 待合成文本
        save_path: 保存路径
        voice: 音色
        model: 模型
    
    Returns:
        音频二进制数据
    """
    tts = CosyVoiceTTS(voice=voice, model=model)
    return tts.synthesize(text, save_path)


# ============================================
# 测试
# ============================================

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    print("\n=== Qwen TTS 测试 ===\n")

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        print("   在 .env 文件中添加: DASHSCOPE_API_KEY=your-api-key")
        exit(1)

    try:
        tts = CosyVoiceTTS()

        print("\n[测试] 语音合成...")
        audio = tts.synthesize(
            "你好，我是AI主播小助手，很高兴认识你！",
            save_path="test_output.bin",
        )
        print(f"  生成音频大小: {len(audio)} bytes")

        print("\n✅ 测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
