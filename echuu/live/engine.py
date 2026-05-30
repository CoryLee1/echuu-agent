"""
echuu 实时引擎（解耦版，支持多语言）。
支持 MP3 转换和实时流式播放。
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from ..core.pattern_analyzer import PatternAnalyzer
from ..generators.example_sampler import ExampleSampler
from ..generators.script_generator_v4 import ScriptGeneratorV4
from .danmaku import DanmakuEvaluator, DanmakuHandler
from .llm_factory import create_llm_client
from .performer import PerformerV3
from .state import Danmaku, PerformanceState, PerformerMemory
from .tts_client import TTSClient
from .language import setup_stream_language_from_topic, StreamLanguageContext
from .audio_player import StreamSimulator


def _find_project_root() -> Path:
    root = Path.cwd()
    while root.name != "echuu-agent" and root.parent != root:
        root = root.parent
    return root


class EchuuLiveEngine:
    """
    echuu 实时直播引擎（整合版）。

    - Phase 1: 预生成完整剧本（默认使用 V4.1）
    - Phase 2: 实时表演 + 记忆系统 + 弹幕互动
    """

    def __init__(self, data_path: Optional[str] = None, llm_provider: Optional[str] = None):
        """
        初始化 echuu 实时引擎。

        Args:
            data_path: 数据文件路径（可选）。
            llm_provider: LLM 提供商 ("gemini", "claude", "openai")。
                          如果未指定，根据可用的 API Key 自动选择。
        """
        self.project_root = _find_project_root()
        load_dotenv(self.project_root / ".env")

        self.llm = create_llm_client(provider=llm_provider)
        self.tts = TTSClient()

        self.analyzer = None
        data_file = Path(data_path) if data_path else self.project_root / "data" / "annotated_clips.json"
        if data_file.exists():
            with data_file.open("r", encoding="utf-8") as f:
                clips = json.load(f)
            self.analyzer = PatternAnalyzer(clips)

        clips_file = self.project_root / "data" / "vtuber_raw_clips_for_notebook_full_30_cleaned.jsonl"
        self.example_sampler = ExampleSampler(str(clips_file)) if clips_file.exists() else None

        self.script_gen = ScriptGeneratorV4(self.llm, self.example_sampler)
        self.danmaku_handler = DanmakuHandler(DanmakuEvaluator())
        self.performer = PerformerV3(self.llm, self.tts, self.danmaku_handler)

        self.scripts_dir = self.project_root / "output" / "scripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        self.state: Optional[PerformanceState] = None
        self.stream_lang_context: Optional[StreamLanguageContext] = None

    def setup(
        self,
        name: str,
        persona: str,
        topic: str,
        background: str = "",
        language: str = "zh",
        character_config: Optional[dict] = None,
        on_phase_callback: Optional[callable] = None,
    ) -> PerformanceState:
        """设置表演参数并生成剧本。"""
        # 在这里我们可以捕获推理过程并传给回调
        self.state = self.create_performance(
            name=name,
            persona=persona,
            background=background,
            topic=topic,
            language=language,
            character_config=character_config,
            on_phase_callback=on_phase_callback,
        )
        print(f"\n表演设置完成: {name} - {topic}")
        print(f"剧本行数: {len(self.state.script_lines)}")
        return self.state

    def create_performance(
        self,
        name: str,
        persona: str,
        background: str,
        topic: str,
        language: str = "zh",
        character_config: Optional[dict] = None,
        on_phase_callback: Optional[callable] = None,
    ) -> PerformanceState:
        """创建表演（预生成完整剧本）。"""
        # 从topic检测并设置直播语言
        self.stream_lang_context = setup_stream_language_from_topic(topic, persona)
        print(f"🌐 语言设置: {self.stream_lang_context.greeting_style}")

        # 如果有回调，发送初始信息
        if on_phase_callback:
            on_phase_callback("Phase 0: 正在初始化创作环境...")

        script_lines = self.script_gen.generate(
            name=name,
            persona=persona,
            background=background,
            topic=topic,
            language=language,
            character_config=character_config or {},
            on_phase_callback=on_phase_callback, # 传递回调给生成器
        )

        self._save_script(script_lines, name, topic)
        self._print_script_preview(script_lines)

        catchphrases = []
        if self.analyzer:
            catchphrases = [cp for cp, _ in self.analyzer.extract_catchphrases(language)[:5]]

        memory = PerformerMemory()
        memory.script_progress["total_lines"] = len(script_lines)
        memory.script_progress["current_stage"] = script_lines[0].stage if script_lines else "Unknown"
        for line in script_lines:
            memory.story_points["upcoming"].extend(line.key_info)

        # 更新performer以使用语言上下文
        self.performer = PerformerV3(
            self.llm,
            self.tts,
            self.danmaku_handler,
            stream_lang_context=self.stream_lang_context
        )

        return PerformanceState(
            name=name,
            persona=persona,
            background=background,
            topic=topic,
            script_lines=script_lines,
            memory=memory,
            catchphrases=catchphrases,
        )

    def run(
        self,
        max_steps: int = 12,
        danmaku_sim: Optional[List[Dict]] = None,
        play_audio: bool = False,
        save_audio: bool = False,
        convert_to_mp3: bool = True,
    ):
        """
        运行表演（生成器）。

        Args:
            max_steps: 最大步数
            danmaku_sim: 弹幕模拟数据
            play_audio: 是否播放音频
            save_audio: 是否保存音频
            convert_to_mp3: 是否转换为 MP3（默认 True，减小文件大小）
        """
        if not self.state:
            raise RuntimeError("请先调用 setup() 或 create_performance()")

        danmaku_by_step = defaultdict(list)
        if danmaku_sim:
            for dm in danmaku_sim:
                step = dm.get("step", 0)
                text = dm.get("text", "")
                user = dm.get("user", "观众")
                danmaku_by_step[step].append(Danmaku.from_text(text, user=user))

        if save_audio and self.tts.enabled:
            self.tts.start_recording()

        print(f"\n{'='*60}")
        print("开始实时表演")
        if save_audio and self.tts.enabled:
            print(f"正在录制... (输出格式: {'MP3' if convert_to_mp3 else 'WAV'})")
        print(f"{'='*60}\n")

        total_steps = min(max_steps, len(self.state.script_lines))
        for step in range(total_steps):
            new_danmaku = danmaku_by_step.get(step, [])
            result = self.performer.step(self.state, new_danmaku)

            step_num = result.get("step", 0)
            stage = result.get("stage", "?")
            action = result.get("action", "continue")
            speech = result.get("speech", "")

            action_icons = {
                "continue": "[CONT]",
                "tease": "[TEASE]",
                "jump": "[JUMP]",
                "improvise": "[IMPROV]",
                "end": "[END]",
            }
            icon = action_icons.get(action, "[CONT]")

            print(f"[Step {step_num}] {stage} {icon} {action.upper()}")
            print(f"  Speech: {speech[:100]}{'...' if len(speech) > 100 else ''}")

            if result.get("danmaku"):
                print(f"  Danmaku: {result['danmaku']}")
                print(
                    "  priority={:.2f}, cost={:.2f}, relevance={:.2f}".format(
                        result.get("priority", 0),
                        result.get("cost", 0),
                        result.get("relevance", 0),
                    )
                )

            if isinstance(result.get("emotion_break"), dict):
                level = result["emotion_break"].get("level", 0)
                level_name = {1: "微破防", 2: "明显破防", 3: "完全破防"}.get(level, f"L{level}")
                trigger = result["emotion_break"].get("trigger", "")
                print(f"  情绪断点: {level_name} - {trigger}")
            if result.get("disfluencies"):
                print(f"  认知特征: {', '.join(result['disfluencies'])}")

            if step_num % 3 == 0:
                print(f"\n{result.get('memory_display', '')}")

            if play_audio and result.get("audio"):
                print("  语音已生成")

            print()

            yield result

            if action == "end":
                break

        if save_audio and self.tts.enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 默认使用 .wav 扩展名（会自动转换为 mp3）
            ext = ".mp3" if convert_to_mp3 else ".wav"
            audio_path = self.scripts_dir / f"{timestamp}_{self.state.name}_{self.state.topic[:20].replace(' ', '_')}_live{ext}"

            # 保存并转换
            self.tts.save_recording(str(audio_path), convert_to_mp3=convert_to_mp3, keep_wav=False)

        print(f"\n{'='*60}")
        print("表演结束！")
        print(f"{'='*60}\n")

        print("最终记忆状态：")
        print(self.state.memory.to_display())

    def run_streaming(
        self,
        max_steps: int = 12,
        danmaku_sim: Optional[List[Dict]] = None,
        save_audio: bool = True,
        convert_to_mp3: bool = True,
    ):
        """
        实时流式直播模式 - 串行播放音频，段落间有自然停顿（1-5秒）

        Args:
            max_steps: 最大步数
            danmaku_sim: 弹幕模拟数据
            save_audio: 是否保存音频
            convert_to_mp3: 是否转换为 MP3（默认 True）
        """
        if not self.state:
            raise RuntimeError("请先调用 setup() 或 create_performance()")

        # 使用 StreamSimulator 进行流式播放
        simulator = StreamSimulator()

        # 设置录制
        if save_audio and self.tts.enabled:
            self.tts.start_recording()

        # 获取生成器
        generator = self.run(
            max_steps=max_steps,
            danmaku_sim=danmaku_sim,
            play_audio=False,  # 不在 run 中播放
            save_audio=False,  # 不在 run 中保存
        )

        # 模拟流式直播
        total_duration = simulator.simulate_live_stream(
            generator,
            show_progress=True,
            show_memory=True
        )

        # 保存音频
        if save_audio and self.tts.enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".mp3" if convert_to_mp3 else ".wav"
            audio_path = self.scripts_dir / f"{timestamp}_{self.state.name}_{self.state.topic[:20].replace(' ', '_')}_live{ext}"
            self.tts.save_recording(str(audio_path), convert_to_mp3=convert_to_mp3, keep_wav=False)

    def _save_script(self, script_lines, name: str, topic: str):
        """保存剧本到 JSON 文件。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = topic[:30].replace(" ", "_").replace("/", "_")
        filename = f"{timestamp}_{name}_{safe_topic}.json"
        filepath = self.scripts_dir / filename

        script_data = {
            "metadata": {
                "timestamp": timestamp,
                "name": name,
                "topic": topic,
                "total_lines": len(script_lines),
            },
            "script": [
                {
                    "id": line.id,
                    "text": line.text,
                    "stage": line.stage,
                    "cost": line.interruption_cost,
                    "key_info": line.key_info,
                    "disfluencies": line.disfluencies,
                    "emotion_break": line.emotion_break,
                    "cue": line.cue.to_dict() if hasattr(line, 'cue') and line.cue else None,
                }
                for line in script_lines
            ],
        }

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        print(f"剧本已保存: {filepath}")

    def _print_script_preview(self, script_lines):
        """打印剧本预览。"""
        print("\n生成的剧本：")
        print("=" * 60)
        for i, line in enumerate(script_lines):
            cost_bar = "#" * int(line.interruption_cost * 5) + "-" * (5 - int(line.interruption_cost * 5))
            print(f"\n[{i}] {line.stage} {cost_bar} cost={line.interruption_cost:.1f}")
            preview = line.text[:80] + ("..." if len(line.text) > 80 else "")
            print(f"    {preview}")
            print(f"    key_info: {', '.join(line.key_info)}")
        print("\n" + "=" * 60 + "\n")
