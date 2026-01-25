"""
通义千问 CosyVoice TTS Client
支持流式和非流式语音合成
"""

import os
import io
from typing import Optional, Callable, List
from pathlib import Path
from datetime import datetime

# 尝试导入 dashscope
try:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback, AudioFormat
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


class CosyVoiceTTS:
    """
    通义千问 CosyVoice TTS 客户端
    
    使用方法:
        tts = CosyVoiceTTS()
        
        # 非流式合成
        audio = tts.synthesize("你好，世界！")
        
        # 流式合成
        tts.synthesize_streaming(["你好，", "世界！"], save_path="output.mp3")
    """
    
    # 音频格式映射
    FORMAT_MAP = {
        "mp3": AudioFormat.MP3_22050HZ_MONO_256KBPS if DASHSCOPE_AVAILABLE else None,
        "wav": AudioFormat.WAV_22050HZ_MONO_16BIT if DASHSCOPE_AVAILABLE else None,
        "pcm": AudioFormat.PCM_22050HZ_MONO_16BIT if DASHSCOPE_AVAILABLE else None,
    }
    
    def __init__(self,
                 api_key: str = None,
                 model: str = None,
                 voice: str = None,
                 audio_format: str = "mp3"):
        """
        初始化 TTS 客户端
        
        Args:
            api_key: DashScope API Key (默认从环境变量读取)
            model: TTS 模型 (默认 cosyvoice-v3-flash)
            voice: 音色 (默认 longanyang)
            audio_format: 音频格式 mp3/wav/pcm
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope 未安装，请运行: pip install dashscope")
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")
        
        dashscope.api_key = self.api_key
        
        self.model = model or os.getenv("TTS_MODEL", "cosyvoice-v3-flash")
        self.voice = voice or os.getenv("TTS_VOICE", "longanyang")
        self.audio_format = self.FORMAT_MAP.get(audio_format.lower(), self.FORMAT_MAP["mp3"])
        
        print(f"✅ TTS Client 初始化: model={self.model}, voice={self.voice}")
    
    def synthesize(self, text: str, save_path: str = None) -> bytes:
        """
        非流式语音合成
        
        Args:
            text: 待合成文本
            save_path: 保存路径 (可选)
        
        Returns:
            音频二进制数据
        """
        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format
        )
        
        audio = synthesizer.call(text)
        
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(audio)
            print(f"[TTS] 音频已保存: {save_path}")
        
        return audio
    
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
        callback = TTSCallback(on_audio=on_audio, save_path=save_path)
        
        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format,
            callback=callback
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
        callback = TTSCallback(on_audio=on_audio, save_path=save_path)
        
        synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=self.audio_format,
            callback=callback
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
    
    print("\n=== CosyVoice TTS 测试 ===\n")
    
    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        print("   在 .env 文件中添加: DASHSCOPE_API_KEY=your-api-key")
        exit(1)
    
    try:
        tts = CosyVoiceTTS()
        
        # 测试非流式
        print("\n[测试1] 非流式合成...")
        audio = tts.synthesize(
            "你好，我是AI主播小助手，很高兴认识你！",
            save_path="test_output.mp3"
        )
        print(f"  生成音频大小: {len(audio)} bytes")
        
        # 测试流式
        print("\n[测试2] 流式合成...")
        texts = [
            "今天天气真不错，",
            "我们来聊聊最近发生的有趣的事情吧。",
            "你有什么想聊的话题吗？"
        ]
        audio = tts.synthesize_streaming(
            texts,
            save_path="test_streaming_output.mp3"
        )
        print(f"  生成音频大小: {len(audio)} bytes")
        
        print("\n✅ 测试完成！音频文件已保存。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
