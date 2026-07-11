"""直播引擎服务"""
import os
import asyncio
import traceback
import shutil
from pathlib import Path
from typing import Callable, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from echuu.live.engine import EchuuLiveEngine
from echuu.live.state import Danmaku
from echuu.live.timeline import TimelineWriter, estimate_wav_duration

try:
    from ..config import SCRIPTS_DIR
    from ..models import LiveConfig
    from ..state import state
    from ..database.models import Character, VoiceConfig, LLMModel, LiveSession, SessionStatus
    from .s3_archive import archive_session_to_s3
except ImportError:
    from config import SCRIPTS_DIR
    from models import LiveConfig
    from state import state
    from database.models import Character, VoiceConfig, LLMModel, LiveSession, SessionStatus
    from services.s3_archive import archive_session_to_s3


def _load_prev_memory_summary(character_name: str, exclude_session: str = "") -> str:
    """读同角色最近一次 session 的记忆摘要（story_points/promises），供跨场 call-back。"""
    import json
    try:
        candidates = sorted(
            (p for p in SCRIPTS_DIR.glob("*/memory.json") if p.parent.name != exclude_session),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        for path in candidates:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("name") != character_name:
                continue
            parts = []
            points = [str(x) for x in (data.get("story_points") or [])[:3]]
            if points:
                parts.append("聊过：" + "；".join(points))
            promises = [str(p.get("content", p)) for p in (data.get("promises") or [])[:2]]
            if promises:
                parts.append("答应过观众：" + "；".join(promises))
            return "。".join(parts)
    except Exception as exc:  # noqa: BLE001 — 记忆注入失败不阻塞开播
        print(f"[memory] 读取上一场记忆失败（跳过）: {exc}")
    return ""


def _dump_session_memory(engine, character_name: str, session_dir: Path) -> None:
    """storytelling 结束后把记忆摘要落盘，供下一场注入。"""
    import json
    try:
        memory = engine.state.memory
        payload = {
            "name": character_name,
            "story_points": memory.story_points.get("mentioned", []),
            "promises": [p for p in memory.promises if not p.get("fulfilled")],
        }
        (session_dir / "memory.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[memory] 记忆落盘失败（跳过）: {exc}")


class LiveService:
    """直播引擎服务"""

    @staticmethod
    async def run_live_engine_inline(
        character_name: str,
        persona: str,
        background: str,
        topic: str,
        voice: str,
        initial_danmaku: List[str],
        session_id: str,
        room_id: str,
        max_steps: int = 15,
        mode: str = "storytelling",
        source: Optional[dict] = None,
        persona_card: Optional[dict] = None,
    ):
        """
        运行直播引擎（内联模式）：跳过数据库，直接使用传入的角色配置。
        TTS 使用环境变量中配置的默认声音，voice 参数会覆盖 TTS_VOICE。

        mode: storytelling（默认）/ reaction / singing_learn。
        source: 模式专属输入，见 InlineStartRequest 注释。
        persona_card: 结构化人设卡（Phase 2-①，可选），贯穿剧本/开场收尾/弹幕回应。
        """
        state.is_running = True
        session_dir = SCRIPTS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        timeline = TimelineWriter(session_dir, mode, meta={
            "name": character_name,
            "topic": topic,
            "voice": voice,
            "source": source or {},
        })

        async def bcast(data: dict):
            await state.broadcast(data, room_id=room_id)

        async def emit_step(result: dict, step_idx: int):
            """统一出口：音频落盘 → timeline 记录 → WS 广播。"""
            audio_data = result.pop("audio", None)
            duration = result.pop("duration", None)
            if audio_data:
                response_format = os.getenv("TTS_RESPONSE_FORMAT", "pcm").lower()
                ext = ".wav" if response_format == "pcm" else f".{response_format}"
                audio_filename = f"step_{step_idx}{ext}"
                with open(session_dir / audio_filename, "wb") as f:
                    f.write(audio_data)
                result["audio_url"] = f"/audio/{session_id}/{audio_filename}"
                if duration is None:
                    duration = estimate_wav_duration(audio_data)
            ev = timeline.append(
                result,
                duration=duration or 0.0,
                t=result.pop("timeline_t", None),
            )
            await bcast({"type": "step", **ev})

        try:
            # 覆盖声音设置
            if voice:
                os.environ["TTS_VOICE"] = voice

            engine = EchuuLiveEngine()
            state.set_engine(engine)

            # 重置停止标志
            state.stop_requested = False

            # 预生产跑在 executor 线程里，on_phase 不能在线程内 get_event_loop()
            main_loop = asyncio.get_running_loop()

            def on_phase(msg: str):
                asyncio.run_coroutine_threadsafe(
                    bcast({"type": "reasoning", "content": msg}),
                    main_loop,
                )

            # ============ 预生产阶段：opening 与主体并行，按模式产出事件 ============
            from itertools import chain
            from echuu.modes.rundown import produce_opening_events, produce_closing_events
            from echuu.modes.topic_brief import produce_topic_brief, merge_brief_into_background
            from echuu.core.persona_card import PersonaCard
            from echuu.live.tts_client import TTSClient

            loop = main_loop
            card = PersonaCard.from_dict(persona_card)

            # 上一场记忆注入：同角色最近一次 session 的记忆摘要 →"上次说过…"是天然跨场 call-back
            prev_memory = _load_prev_memory_summary(character_name, exclude_session=session_id)
            if prev_memory:
                background = f"{background}\n\n【上一场直播的记忆】{prev_memory}" if background else \
                    f"【上一场直播的记忆】{prev_memory}"
                on_phase("已载入上一场直播的记忆")

            # 主题语义 grounding：联网确认网络流行语的真实用法（如"云养猫"），
            # 结果注入 background，opening 与三模式主体共享。失败/不支持时为空，不阻塞。
            on_phase("正在联网确认主题语义…")
            topic_brief = await loop.run_in_executor(
                None, lambda: produce_topic_brief(engine.llm, topic),
            )
            background = merge_brief_into_background(background, topic, topic_brief)
            if topic_brief:
                on_phase(f"主题背景已就绪：{topic_brief[:48]}…")
            # rundown 用独立 TTS client：与主体预生产并行跑，共享 client 的
            # set_instruction 会串音
            rundown_tts = TTSClient()

            def produce_opening_safe():
                try:
                    return produce_opening_events(
                        engine, character_name, persona, topic, mode,
                        on_phase=on_phase, tts=rundown_tts, card=card,
                    )
                except Exception as exc:  # opening 失败不阻塞开播
                    print(f"[rundown] opening 生成失败（跳过）: {exc}")
                    return []

            if mode == "reaction":
                from echuu.modes.reaction import produce_reaction_events
                opening_events, events = await asyncio.gather(
                    loop.run_in_executor(None, produce_opening_safe),
                    loop.run_in_executor(
                        None,
                        lambda: produce_reaction_events(
                            engine, character_name, persona, background, topic,
                            source or {}, on_phase=on_phase,
                        ),
                    ),
                )
                generator = iter(events)
            elif mode == "singing_learn":
                from echuu.modes.singing import produce_singing_events
                opening_events, events = await asyncio.gather(
                    loop.run_in_executor(None, produce_opening_safe),
                    loop.run_in_executor(
                        None,
                        lambda: produce_singing_events(
                            engine, character_name, persona, background, topic,
                            source or {}, session_dir, on_phase=on_phase,
                        ),
                    ),
                )
                generator = iter(events)
            else:
                # storytelling（默认）：现有引擎路径，保留弹幕实时穿插
                for dm_text in (initial_danmaku or []):
                    dm = Danmaku.from_text(dm_text, user="观众")
                    engine.state.danmaku_queue.append(dm)

                opening_events, _ = await asyncio.gather(
                    loop.run_in_executor(None, produce_opening_safe),
                    loop.run_in_executor(
                        None,
                        lambda: engine.setup(
                            name=character_name,
                            persona=persona,
                            background=background,
                            topic=topic,
                            on_phase_callback=on_phase,
                            persona_card=persona_card,
                        ),
                    ),
                )

                # 复制剧本到 session 目录
                script_sources = sorted(engine.scripts_dir.glob("*.json"), key=os.path.getmtime)
                if script_sources:
                    shutil.copy(script_sources[-1], session_dir / "full_script.json")

                generator = engine.run(max_steps=max_steps, play_audio=False, save_audio=True)

            # 开场段先播（stage='opening'，前端按 stage 走 sequential 通道）
            generator = chain(opening_events, generator)

            await bcast({
                "type": "ready",
                "content": f"剧本已生成，Session: {session_id}",
                "session_id": session_id,
                "mode": mode,
            })

            # ============ 表演阶段：统一事件循环 ============
            step_idx = 0
            for result in generator:
                if state.stop_requested:
                    break

                await emit_step(result, step_idx)

                # 广播 memory 事件（storytelling 专属）
                if mode == "storytelling" and engine.state:
                    memory = engine.state.memory
                    await bcast({
                        "type": "memory",
                        "memory": {
                            "story_points": memory.story_points.get("mentioned", []),
                            "promises": [p for p in memory.promises if not p.get("fulfilled")],
                            "emotion_trend": [e["level"] for e in memory.emotion_track[-5:]],
                        },
                    })

                step_idx += 1
                await asyncio.sleep(0.1)

            # ============ 收尾段：自然结束才播，用户主动 stop 跳过 ============
            if not state.stop_requested:
                def produce_closing_safe():
                    try:
                        return produce_closing_events(
                            engine, character_name, persona, topic, mode,
                            on_phase=on_phase, tts=rundown_tts, card=card,
                        )
                    except Exception as exc:  # closing 失败不阻塞收播
                        print(f"[rundown] closing 生成失败（跳过）: {exc}")
                        return []

                for result in await loop.run_in_executor(None, produce_closing_safe):
                    if state.stop_requested:
                        break
                    await emit_step(result, step_idx)
                    step_idx += 1

            await bcast({
                "type": "success",
                "session_id": session_id,
                "content": "表演圆满结束",
            })

            # 记忆落盘：下一场同角色开播时注入"上次说过…"
            if mode == "storytelling" and engine.state:
                _dump_session_memory(engine, character_name, session_dir)

            # 归档音频+脚本到 S3（失败只 log 不中断）
            try:
                uploaded = await archive_session_to_s3(session_id, session_dir)
                await bcast({
                    "type": "archived",
                    "session_id": session_id,
                    "uploaded_count": uploaded,
                })
            except Exception as archive_err:
                print(f"[archive] S3 归档失败（不影响直播结束）: {archive_err}")

        except Exception as e:
            await bcast({"type": "error", "content": str(e)})
            print(traceback.format_exc())
        finally:
            state.is_running = False
            state.clear_engine()

    @staticmethod
    async def run_live_engine(
        character_id: str,
        config: LiveConfig,
        session_id: str,
        user_id: str
    ):
        """
        运行直播引擎任务（数据库模式）

        Args:
            character_id: 角色ID
            config: 直播配置
            session_id: Session ID
            user_id: 用户ID
        """
        state.is_running = True
        session_dir = SCRIPTS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        try:
            from ..database.database import SessionLocal
        except ImportError:
            from database.database import SessionLocal

        db = SessionLocal()
        live_session = None

        room_id = state.current_room_id

        async def bcast(data: dict):
            await state.broadcast(data, room_id=room_id)

        try:
            character = db.query(Character).filter(Character.id == character_id).first()
            if not character:
                raise ValueError(f"角色不存在: {character_id}")

            voice_config_id = config.voice_config_id
            if voice_config_id:
                voice_config = db.query(VoiceConfig).filter(VoiceConfig.id == voice_config_id).first()
            else:
                voice_config = db.query(VoiceConfig).filter(
                    VoiceConfig.character_id == character_id,
                    VoiceConfig.is_default == True
                ).first()

            if not voice_config:
                raise ValueError("未找到声音配置")

            llm_model_id = config.llm_model_id or character.default_llm_model_id
            if llm_model_id:
                llm_model = db.query(LLMModel).filter(LLMModel.id == llm_model_id).first()
            else:
                llm_model = db.query(LLMModel).filter(LLMModel.is_default == True).first()

            if not llm_model:
                raise ValueError("未找到LLM模型")

            live_session = LiveSession(
                session_id=session_id,
                user_id=user_id,
                character_id=character_id,
                topic=config.topic,
                llm_model_id=llm_model.id,
                voice_config_id=voice_config.id,
                vtuber_3d_model_id=config.vtuber_3d_model_id,
                status=SessionStatus.RUNNING,
                script_path=str(session_dir / "full_script.json"),
                audio_dir=str(session_dir),
                started_at=datetime.utcnow(),
            )
            db.add(live_session)
            db.commit()
            db.refresh(live_session)

            os.environ["TTS_MODEL"] = voice_config.tts_model
            os.environ["TTS_VOICE"] = voice_config.voice_name

            if llm_model.api_key_env:
                api_key = os.getenv(llm_model.api_key_env)
                if api_key:
                    os.environ["DEFAULT_MODEL"] = llm_model.model_id

            engine = EchuuLiveEngine()
            state.set_engine(engine)

            db_main_loop = asyncio.get_running_loop()

            def on_phase(msg: str):
                asyncio.run_coroutine_threadsafe(
                    bcast({"type": "reasoning", "content": msg}),
                    db_main_loop,
                )

            engine.setup(
                name=character.name,
                persona=character.persona,
                background=character.background or "",
                topic=config.topic,
                on_phase_callback=on_phase,
            )

            script_sources = sorted(engine.scripts_dir.glob("*.json"), key=os.path.getmtime)
            if script_sources:
                shutil.copy(script_sources[-1], session_dir / "full_script.json")

            await bcast({
                "type": "ready",
                "content": f"剧本已生成并归档至 {session_id}",
                "session_id": session_id,
            })

            state.stop_requested = False
            step_idx = 0
            for result in engine.run(
                max_steps=config.max_steps,
                play_audio=False,
                save_audio=True
            ):
                if state.stop_requested:
                    break

                audio_data = result.get("audio")
                if audio_data:
                    response_format = os.getenv("TTS_RESPONSE_FORMAT", "pcm").lower()
                    ext = ".wav" if response_format == "pcm" else f".{response_format}"
                    audio_filename = f"step_{step_idx}{ext}"
                    with open(session_dir / audio_filename, "wb") as f:
                        f.write(audio_data)
                    result["audio_url"] = f"/audio/{session_id}/{audio_filename}"
                    result.pop("audio", None)

                # 广播 step 事件（扁平化）
                await bcast({"type": "step", **result})

                # 广播 memory 事件
                memory = engine.state.memory
                await bcast({
                    "type": "memory",
                    "memory": {
                        "story_points": memory.story_points.get("mentioned", []),
                        "promises": [p for p in memory.promises if not p.get("fulfilled")],
                        "emotion_trend": [e["level"] for e in memory.emotion_track[-5:]],
                    },
                })

                step_idx += 1
                await asyncio.sleep(0.1)

            await bcast({
                "type": "success",
                "session_id": session_id,
                "content": "表演圆满结束",
            })

            # 归档音频+脚本到 S3（失败只 log 不中断）
            try:
                uploaded = await archive_session_to_s3(session_id, session_dir)
                await bcast({
                    "type": "archived",
                    "session_id": session_id,
                    "uploaded_count": uploaded,
                })
            except Exception as archive_err:
                print(f"[archive] S3 归档失败（不影响直播结束）: {archive_err}")

            live_session.status = SessionStatus.COMPLETED
            live_session.ended_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            await bcast({"type": "error", "content": str(e)})
            print(traceback.format_exc())

            if live_session:
                try:
                    live_session.status = SessionStatus.FAILED
                    live_session.ended_at = datetime.utcnow()
                    db.commit()
                except Exception:
                    db.rollback()
        finally:
            state.is_running = False
            state.clear_engine()
            if db:
                db.close()

    @staticmethod
    def inject_danmaku(text: str, user: str = "观众"):
        """
        注入实时弹幕

        Args:
            text: 弹幕文本
            user: 用户名
        """
        if not state.is_running or not state.current_engine:
            raise ValueError("直播未运行")

        dm = Danmaku.from_text(text, user=user)
        state.current_engine.state.danmaku_queue.append(dm)
        return dm
