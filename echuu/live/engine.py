"""
echuu 实时引擎（解耦版，支持多语言）。
支持 MP3 转换和实时流式播放。
"""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from ..core.pattern_analyzer import PatternAnalyzer
from ..core.persona_model import PersonaModel, RichPersona
from ..core.persona_analyst import PersonaAnalyst
from ..core.story_core import StoryCore
from ..core.unit import Show
from ..core.unit_planner import UnitPlanner
from ..core.structure_breaker import StructureBreaker
from ..generators.example_sampler import ExampleSampler
from ..generators.script_writer import ScriptWriter
from .danmaku import DanmakuEvaluator, DanmakuHandler
from .danmaku_interleave import DanmakuInterleaver
from .llm_factory import create_llm_client
from .performer import PerformerV3
from .state import Danmaku, PerformanceState, PerformerMemory
from .tts_client import TTSClient
from .language import setup_stream_language_from_topic, StreamLanguageContext
from .motion import pick_motion_for_danmaku, pick_motion_for_step
from .audio_player import StreamSimulator


def _find_project_root() -> Path:
    root = Path.cwd()
    while root.name != "echuu-agent" and root.parent != root:
        root = root.parent
    return root


class _LLMGenerateAdapter:
    """Bridge the engine's LLM client (`.call(prompt, system=, max_tokens=)`)
    to the `.generate(prompt) -> str` contract that PersonaModel and
    ScriptWriter / PersonaAnalyst expect.

    The V5 modules were unit-tested against a `.generate` stub; real clients
    (Gemini / Claude / OpenAI) only expose `.call`. This adapter keeps the
    modules client-agnostic without leaking the LLM interface into them.
    """

    def __init__(self, client, max_tokens: int = 8000) -> None:
        self._client = client
        self._max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        # Prefer a native .generate if a future client provides one.
        native = getattr(self._client, "generate", None)
        if callable(native):
            return native(prompt)
        return self._client.call(prompt, max_tokens=self._max_tokens)


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

        # V5 modules expect a `.generate(prompt)` LLM contract; real clients
        # expose `.call(...)`. Adapt once, here, at the engine boundary.
        self.llm_gen = _LLMGenerateAdapter(self.llm)

        self.persona_analyst = PersonaAnalyst()
        self.unit_planner = UnitPlanner()
        self.structure_breaker = StructureBreaker()
        # Phase 2-①：用户人设卡 + call-back 埋梗账本（create_performance 里填充）
        self.persona_card = None
        from ..core.gag_ledger import GagLedger as _GagLedger
        self.gag_ledger = _GagLedger()
        self.script_writer = ScriptWriter(self.llm_gen, self.example_sampler)
        self.danmaku_handler = DanmakuHandler(DanmakuEvaluator())
        self.danmaku_interleaver = DanmakuInterleaver(self.llm_gen)
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
        persona_card: Optional[dict] = None,
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
            persona_card=persona_card,
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
        persona_card: Optional[dict] = None,
    ) -> PerformanceState:
        """V2: PersonaAnalyst → UnitPlanner(自适应段数) → ScriptWriter → 去升华。"""
        from echuu.core.persona_card import PersonaCard

        self.stream_lang_context = setup_stream_language_from_topic(topic, persona)
        print(f"🌐 语言设置: {self.stream_lang_context.greeting_style}")

        # 用户人设卡（可选）：口癖/称呼/雷点等硬约束，贯穿 analyst/writer/弹幕回应
        self.persona_card = PersonaCard.from_dict(persona_card)
        if self.persona_card:
            print(f"🎴 人设卡已加载: 口癖={list(self.persona_card.speech_tics)}, "
                  f"观众称呼={self.persona_card.audience_nickname or '（无）'}")

        if on_phase_callback:
            on_phase_callback("Phase A: 分析人设三轴 + 故事内核...")
        rich_persona, story_core = self.persona_analyst.analyze(
            name=name, persona=persona, topic=topic, background=background, llm=self.llm_gen,
            card=self.persona_card,
        )

        if on_phase_callback:
            on_phase_callback("Phase B: 排时间/音色骨架...")
        # 节目长度自适应：故事撑得起几段就播几段（2~4 段 ≈ 2.5~5 分钟）
        n_units = max(2, min(4, len(story_core.story_beats) or 4))
        units = self.unit_planner.plan(n_units)
        print(f"🎚️ 节目长度: {len(units)} 段 (~{int(len(units) * 75 / 60)}min，按故事自适应)")

        if on_phase_callback:
            on_phase_callback("Phase C: 抽相关 few-shot + 编剧创作...")
        examples = ""
        if self.example_sampler:
            lang = "en" if str(language).lower().startswith("en") else "zh"
            examples = self.example_sampler.get_relevant_examples(
                topic=topic, persona=persona, n=3, language=lang,
            )
        n_ex = examples.count("真实案例") if examples else 0
        print(f"📚 few-shot 示例注入: {n_ex} 条 (sampler={'on' if self.example_sampler else 'off'})")
        units = self.script_writer.write(
            rich_persona, story_core, units, examples=examples, topic=topic,
            card=self.persona_card,
        )

        # call-back 埋梗账本：writer 埋的意象优先，兜底用生活化锚点（closing 回收用）
        from echuu.core.gag_ledger import GagLedger
        self.gag_ledger = GagLedger()
        self.gag_ledger.register(
            self.script_writer.last_planted_gags or list(rich_persona.life_anchors[:1]),
        )
        if len(self.gag_ledger):
            print(f"🪃 已埋梗: {self.gag_ledger.unrecalled()}")

        if on_phase_callback:
            on_phase_callback("Phase D: 清洗升华...")
        for u in units:
            self.structure_breaker.delete_sublimation_in_unit(u)

        show = Show(persona=rich_persona, topic=topic, units=units, story_core=story_core)

        # Flatten units → script_lines for V4-compat consumers (PerformerV3, _save_script)
        flat_lines = [line for u in show.units for line in u.lines]

        catchphrases = []
        if self.analyzer:
            catchphrases = [cp for cp, _ in self.analyzer.extract_catchphrases(language)[:5]]

        memory = PerformerMemory()
        memory.script_progress["total_lines"] = len(flat_lines)
        memory.script_progress["current_stage"] = flat_lines[0].stage if flat_lines else "hook"

        self.performer = PerformerV3(
            self.llm,
            self.tts,
            self.danmaku_handler,
            stream_lang_context=self.stream_lang_context,
        )

        self._save_script_v5(show, name, topic)
        self._print_script_preview_v5(show)

        return PerformanceState(
            name=name,
            persona=persona,
            background=background,
            topic=topic,
            show=show,
            script_lines=flat_lines,  # compat
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
        segment_gap_ms: int = 0,
    ):
        """V5 实时表演（按 unit 渲染，per-unit acoustic switching）。"""
        if not self.state or not getattr(self.state, "show", None):
            raise RuntimeError("请先调用 setup() — Show 未生成")

        # Pre-populate danmaku queue (sim mode)
        if danmaku_sim:
            for dm in danmaku_sim:
                text = dm.get("text", "")
                user = dm.get("user", "观众")
                self.state.danmaku_queue.append(Danmaku.from_text(text, user=user))

        if save_audio and self.tts.enabled:
            self.tts.start_recording()

        print(f"\n{'='*60}")
        print("开始实时表演 (V5)")
        if save_audio and self.tts.enabled:
            print(f"正在录制... (输出格式: {'MP3' if convert_to_mp3 else 'WAV'})")
        print(f"{'='*60}\n")

        # 弹幕穿插的节奏控制：每讲完一行后可能插一条回应（冷却+每单元上限）
        lines_since_resp = 0
        resp_in_unit = 0
        last_unit_idx = -1
        last_line_text = ""
        # 互动窗口（Phase 2-①）：interact 行抛出问题后 N 行内冷却减半、上限翻倍；
        # 一行之后弹幕仍空 → 自嘲兜底一句（人设化生成，不写死）
        interact_window = 0
        interact_question = ""
        quip_armed = False

        for ev in self._render_show():
            unit_idx = ev["unit"]["index"]
            if unit_idx != last_unit_idx:
                resp_in_unit = 0          # 进新单元，回应额度重置
                last_unit_idx = unit_idx
            self.state.current_unit_idx = unit_idx
            self.state.current_line_in_unit = ev["line"]["index_in_unit"]
            # 切块后 max_steps 仍按"行"计：只在行首块 +1，行中间不 break
            is_first_chunk = ev["line"].get("chunk_index", 0) == 0
            is_last_chunk = ev["line"].get("chunk_last", True)
            if is_first_chunk:
                self.state.current_step += 1
            self.state.memory.script_progress["current_line"] = self.state.current_step
            self.state.memory.script_progress["current_stage"] = ev["line"]["stage"]
            last_line_text = ev["line"]["text"]

            print(f"[Unit {unit_idx+1}/{len(self.state.show.units)} · {ev['line']['stage']}] {last_line_text[:80]}{'...' if len(last_line_text) > 80 else ''}")
            if ev["line"]["is_rupture"] and is_first_chunk:
                print(f"  💥 rupture_kind={ev['unit']['rupture_kind']}")

            yield ev
            if not is_last_chunk:
                continue  # 行没播完不计弹幕冷却、不判停
            lines_since_resp += 1

            # interact 行落地 → 开互动窗口
            if ev["line"]["stage"] == "interact":
                interact_window = 4
                interact_question = last_line_text
                quip_armed = True
                print(f"  🙋 互动点已抛出，窗口开启: {interact_question[:40]}")
            elif interact_window > 0:
                interact_window -= 1

            if self.state.current_step >= max_steps:
                break

            # 自然断点：穿插一条弹幕回应（常规：冷却 ≥2 行、每单元 ≤1 条；
            # 互动窗口内：冷却减半、每单元上限翻倍）
            in_window = interact_window > 0
            cooldown_ok = lines_since_resp >= (1 if in_window else 2)
            quota_ok = resp_in_unit < (2 if in_window else 1)
            if cooldown_ok and quota_ok and self.state.danmaku_queue:
                resp_ev = self._maybe_interleave_danmaku(unit_idx, last_line_text)
                if resp_ev is not None:
                    resp_in_unit += 1
                    lines_since_resp = 0
                    quip_armed = False  # 有人理了，不用自嘲
                    self.state.current_step += 1
                    print(f"  💬 回应弹幕[{resp_ev['danmaku']['user']}]: {resp_ev['speech'][:60]}")
                    yield resp_ev
                    if self.state.current_step >= max_steps:
                        break
            # 互动点抛出一行之后弹幕仍空 → 自嘲兜底（只一次）
            elif quip_armed and interact_window == 3 and not self.state.danmaku_queue:
                quip_armed = False
                quip_ev = self._maybe_no_reaction_quip(unit_idx, interact_question)
                if quip_ev is not None:
                    self.state.current_step += 1
                    print(f"  🫥 没人理，自嘲兜底: {quip_ev['speech'][:50]}")
                    yield quip_ev
                    if self.state.current_step >= max_steps:
                        break

        if save_audio and self.tts.enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".mp3" if convert_to_mp3 else ".wav"
            audio_path = self.scripts_dir / f"{timestamp}_{self.state.name}_{self.state.topic[:20].replace(' ', '_')}_live{ext}"
            self.tts.save_recording(str(audio_path), convert_to_mp3=convert_to_mp3,
                                    keep_wav=False, gap_ms=segment_gap_ms)

        print(f"\n{'='*60}\n表演结束！\n{'='*60}\n")

    def _render_show(self):
        """Iterate through Show.units, switching acoustic per unit.

        Yields one step-event dict per line. TTS failures yield audio=None
        but do NOT abort the loop (spec §5)."""
        from dataclasses import asdict as _asdict
        from .tts_instruction import build_instruction, infer_cls
        from .breath import chunk_text
        show = self.state.show
        for unit in show.units:
            self.tts.update_session(**_asdict(unit.acoustic))
            for line_in_unit, line in enumerate(unit.lines):
                self.tts.set_instruction(build_instruction(unit, line))
                # 长台词按呼吸组切成短 step：字幕短、动作切换勤、step 间自带换气
                chunks = chunk_text(line.text) or [line.text]
                for ci, chunk in enumerate(chunks):
                    try:
                        audio = self.tts.synthesize(chunk)
                    except Exception:
                        audio = None
                    ev = self._build_step_event(
                        unit, line_in_unit, line, audio,
                        text=chunk, chunk_index=ci, chunk_last=(ci == len(chunks) - 1),
                    )
                    ev["cls"] = infer_cls(unit, line)
                    yield ev

    def _build_step_event(self, unit, line_in_unit: int, line, audio,
                          text: str = None, chunk_index: int = 0, chunk_last: bool = True):
        """Construct WS-bound step event payload. v2 schema (spec §3.2).

        text/chunk_*：长台词切块时本 step 的实际文本与块位置；
        续块不重发动作 hint（保持 idle，前端文本语义匹配仍可触发手势）。
        pause_after：本行播完后的"思考停顿"秒数——interact 行等观众反应、
        unit 收尾行喘口气想下一段；前端在换气间隙上叠加，避免连珠炮输出。
        """
        from dataclasses import asdict as _asdict
        speech = text if text is not None else line.text
        pause_after = 0.0
        if chunk_last:
            if line.stage == "interact":
                pause_after = round(random.uniform(6.0, 10.0), 1)
            elif line_in_unit == len(unit.lines) - 1:
                pause_after = round(random.uniform(5.0, 8.0), 1)
        return {
            "type": "step",
            "show": {
                "total_units": len(self.state.show.units),
                "total_lines": sum(len(u.lines) for u in self.state.show.units),
            },
            "unit": {
                "index": unit.index,
                "axis": unit.axis,
                "density": unit.density,
                "time_window": list(unit.time_window),
                "acoustic": _asdict(unit.acoustic),
                "rupture_kind": next((r.kind for r in unit.rupture_slots), None) if line.is_rupture else None,
            },
            "line": {
                "index_in_unit": line_in_unit,
                "stage": line.stage,
                "text": speech,
                "is_rupture": line.is_rupture,
                "chunk_index": chunk_index,
                "chunk_last": chunk_last,
                "cue": _asdict(line.cue) if hasattr(line.cue, "__dataclass_fields__") and line.cue else None,
            },
            "speech": speech,  # compat alias for audio-caption sync (spec §3.2)
            "pause_after": pause_after,
            "motion": pick_motion_for_step(unit, line, line_in_unit) if chunk_index == 0
                      else {"state": "idle", "loop": True},
            "audio": audio,
        }

    def _pick_danmaku(self):
        """从队列里挑一条最该回应的弹幕（SC > 问题 > 其它），并移除它。"""
        q = self.state.danmaku_queue
        if not q:
            return None
        # 稳定优先级：SC 优先，其次问题，其余按到达顺序
        best_i, best_key = 0, (-1, -1)
        for i, d in enumerate(q):
            key = (1 if getattr(d, "is_sc", False) else 0,
                   1 if d.is_question() else 0)
            if key > best_key:
                best_key, best_i = key, i
        return q.pop(best_i)

    def _maybe_interleave_danmaku(self, unit_idx: int, last_line: str):
        """生成一条人设化弹幕回应并构造 step 事件；失败返回 None（跳过穿插）。"""
        dm = self._pick_danmaku()
        if dm is None:
            return None
        persona = getattr(self.state.show, "persona", None)
        identity = getattr(persona, "identity", "") if persona else ""
        verbal_tics = getattr(persona, "verbal_tics", ()) if persona else ()
        reply = self.danmaku_interleaver.respond(
            identity=identity, verbal_tics=verbal_tics, topic=self.state.topic,
            last_line=last_line, danmaku_text=dm.text, user=dm.user,
            card=getattr(self, "persona_card", None),
            gags=self.gag_ledger.unrecalled() if getattr(self, "gag_ledger", None) else None,
        )
        if not reply:
            return None
        try:
            audio = self.tts.synthesize(reply) if getattr(self, "tts", None) else None
        except Exception:
            audio = None
        unit = self.state.show.units[unit_idx]
        return self._build_danmaku_event(unit, dm, reply, audio)

    def _maybe_no_reaction_quip(self, unit_idx: int, question: str):
        """互动点没人理时的自嘲兜底 step（人设化生成，失败返回 None 直接跳过）。"""
        persona = getattr(self.state.show, "persona", None)
        quip = self.danmaku_interleaver.no_reaction_quip(
            identity=getattr(persona, "identity", "") if persona else "",
            verbal_tics=getattr(persona, "verbal_tics", ()) if persona else (),
            topic=self.state.topic,
            question=question,
        )
        if not quip:
            return None
        try:
            audio = self.tts.synthesize(quip) if getattr(self, "tts", None) else None
        except Exception:
            audio = None
        unit = self.state.show.units[unit_idx]
        ev = self._build_danmaku_event(unit, None, quip, audio)
        ev.pop("danmaku", None)
        ev["is_danmaku_response"] = False
        ev["line"]["stage"] = "interact_quip"
        return ev

    def _build_danmaku_event(self, unit, danmaku, reply: str, audio):
        """弹幕回应的 step 事件（v2 形状 + danmaku 字段，line.stage='danmaku'）。"""
        from dataclasses import asdict as _asdict
        return {
            "type": "step",
            "show": {
                "total_units": len(self.state.show.units),
                "total_lines": sum(len(u.lines) for u in self.state.show.units),
            },
            "unit": {
                "index": unit.index,
                "axis": unit.axis,
                "density": unit.density,
                "time_window": list(unit.time_window),
                "acoustic": _asdict(unit.acoustic),
                "rupture_kind": None,
            },
            "line": {
                "index_in_unit": -1,
                "stage": "danmaku",
                "text": reply,
                "is_rupture": False,
                "cue": None,
            },
            "speech": reply,
            "danmaku": {"text": danmaku.text, "user": danmaku.user} if danmaku else None,
            "is_danmaku_response": danmaku is not None,
            "motion": pick_motion_for_danmaku(unit, danmaku) if danmaku else {"state": "speaking"},
            "audio": audio,
        }

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

    def _save_script_v5(self, show, name: str, topic: str):
        """V5 Show → JSON dump."""
        from dataclasses import asdict
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = topic[:30].replace(" ", "_").replace("/", "_")
        filename = f"{timestamp}_{name}_{safe_topic}.json"
        filepath = self.scripts_dir / filename

        script_data = {
            "metadata": {
                "timestamp": timestamp,
                "name": name,
                "topic": topic,
                "total_units": len(show.units),
                "total_lines": sum(len(u.lines) for u in show.units),
            },
            "persona": asdict(show.persona),
            "units": [
                {
                    "index": u.index,
                    "time_window": list(u.time_window),
                    "axis": u.axis,
                    "density": u.density,
                    "acoustic": asdict(u.acoustic),
                    "rupture_slots": [asdict(r) for r in u.rupture_slots],
                    "lines": [
                        {
                            "id": l.id,
                            "text": l.text,
                            "stage": l.stage,
                            "is_rupture": l.is_rupture,
                            "interruption_cost": l.interruption_cost,
                        }
                        for l in u.lines
                    ],
                }
                for u in show.units
            ],
        }

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        print(f"V5 剧本已保存: {filepath}")

    def _print_script_preview_v5(self, show):
        """V5 Show → console preview."""
        print("\n生成的剧本（V5）：")
        print("=" * 60)
        for u in show.units:
            print(f"\n--- Unit {u.index + 1} / 4 · axis={u.axis} · density={u.density} ---")
            print(f"  acoustic: pitch={u.acoustic.pitch_rate}, rate={u.acoustic.speech_rate}, vol={u.acoustic.volume}")
            for i, line in enumerate(u.lines):
                rupture_marker = " 💥" if line.is_rupture else ""
                preview = line.text[:80] + ("..." if len(line.text) > 80 else "")
                print(f"  [{i}] {line.stage}{rupture_marker}  {preview}")
        print("\n" + "=" * 60 + "\n")
