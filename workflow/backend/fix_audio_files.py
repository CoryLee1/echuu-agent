"""
修复音频文件：将PCM格式的.mp3文件转换为WAV格式
"""

import struct
from pathlib import Path
import sys

# 确保项目根目录可导入
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    将PCM数据转换为WAV格式
    
    Args:
        pcm_data: PCM原始音频数据
        sample_rate: 采样率（默认24000Hz）
        channels: 声道数（默认1=单声道）
        sample_width: 采样位深（默认2字节=16bit）
    
    Returns:
        WAV格式的音频数据
    """
    data_size = len(pcm_data)
    file_size = 36 + data_size
    
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',           # ChunkID
        file_size,        # ChunkSize
        b'WAVE',          # Format
        b'fmt ',          # Subchunk1ID
        16,               # Subchunk1Size (PCM)
        1,                # AudioFormat (PCM)
        channels,         # NumChannels
        sample_rate,      # SampleRate
        sample_rate * channels * sample_width,  # ByteRate
        channels * sample_width,  # BlockAlign
        sample_width * 8,  # BitsPerSample
        b'data',          # Subchunk2ID
        data_size         # Subchunk2Size
    )
    
    return wav_header + pcm_data


def fix_audio_file(input_path: str, output_path: str = None, sample_rate: int = 24000):
    """
    修复音频文件：将PCM格式的.mp3文件转换为WAV
    
    Args:
        input_path: 输入的.mp3文件路径（实际是PCM数据）
        output_path: 输出的.wav文件路径（如果为None，自动生成）
        sample_rate: 采样率（默认24000Hz）
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ 文件不存在: {input_path}")
        return False
    
    if output_path is None:
        output_file = input_file.with_suffix('.wav')
    else:
        output_file = Path(output_path)
    
    try:
        # 读取PCM数据
        with input_file.open('rb') as f:
            pcm_data = f.read()
        
        if len(pcm_data) == 0:
            print(f"❌ 文件为空: {input_path}")
            return False
        
        # 转换为WAV
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate)
        
        # 保存WAV文件
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('wb') as f:
            f.write(wav_data)
        
        print(f"✅ 转换成功: {input_file.name} -> {output_file.name}")
        print(f"   原始大小: {len(pcm_data)} bytes")
        print(f"   WAV大小: {len(wav_data)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {input_path}")
        print(f"   错误: {e}")
        return False


def main():
    project_root = Path(__file__).resolve().parents[2]
    scripts_dir = project_root / "output" / "scripts"
    
    # 要修复的文件列表
    files_to_fix = [
        "20260128_223335_六螺_关于上司的超劲爆八卦_live.mp3",
        "20260128_223619_六螺_大学时全班开卷考，但只有自己以为闭卷考结_live.mp3",
        "20260128_223905_六螺_第一次养猫时把猫粮当零食吃了_live.mp3",
    ]
    
    print("="*70)
    print("音频文件修复工具")
    print("="*70 + "\n")
    
    success_count = 0
    for filename in files_to_fix:
        input_path = scripts_dir / filename
        print(f"\n处理文件: {filename}")
        if fix_audio_file(str(input_path)):
            success_count += 1
    
    print("\n" + "="*70)
    print(f"修复完成: {success_count}/{len(files_to_fix)} 个文件")
    print("="*70 + "\n")
    
    if success_count > 0:
        print("💡 提示：")
        print("   - 原始.mp3文件已保留（实际是PCM数据）")
        print("   - 新的.wav文件可以直接播放")
        print("   - 建议删除旧的.mp3文件以避免混淆")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
