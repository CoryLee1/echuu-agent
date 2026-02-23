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

try:
    from ..config import SCRIPTS_DIR
    from ..models import LiveConfig
    from ..state import state
    from ..database.models import Character, VoiceConfig, LLMModel, LiveSession, SessionStatus
except ImportError:
    from config import SCRIPTS_DIR
    from models import LiveConfig
    from state import state
    from database.models import Character, VoiceConfig, LLMModel, LiveSession, SessionStatus


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
    ):
        """
        运行直播引擎（内联模式）：跳过数据库，直接使用传入的角色配置。
        TTS 使用环境变量中配置的默认声音，voice 参数会覆盖 TTS_VOICE。
        """
        state.is_running = True
        session_dir = SCRIPTS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        async def bcast(data: dict):
            await state.broadcast(data, room_id=room_id)

        try:
            # 覆盖声音设置
            if voice:
                os.environ["TTS_VOICE"] = voice

            engine = EchuuLiveEngine()
            state.set_engine(engine)

            # 重置停止标志
            state.stop_requested = False

            # 注入初始弹幕
            for dm_text in (initial_danmaku or []):
                dm = Danmaku.from_text(dm_text, user="观众")
                engine.state.danmaku_queue.append(dm)

            def on_phase(msg: str):
                asyncio.run_coroutine_threadsafe(
                    bcast({"type": "reasoning", "content": msg}),
                    asyncio.get_event_loop()
                )

            engine.setup(
                name=character_name,
                persona=persona,
                background=background,
                topic=topic,
                on_phase_callback=on_phase,
            )

            # 复制剧本到 session 目录
            script_sources = sorted(engine.scripts_dir.glob("*.json"), key=os.path.getmtime)
            if script_sources:
                shutil.copy(script_sources[-1], session_dir / "full_script.json")

            await bcast({
                "type": "ready",
                "content": f"剧本已生成，Session: {session_id}",
                "session_id": session_id,
            })

            # Phase 2: 执行
            step_idx = 0
            for result in engine.run(max_steps=max_steps, play_audio=False, save_audio=True):
                if state.stop_requested:
                    break

                # 处理音频文件
                audio_data = result.get("audio")
                if audio_data:
                    response_format = os.getenv("TTS_RESPONSE_FORMAT", "pcm").lower()
                    ext = ".wav" if response_format == "pcm" else f".{response_format}"
                    audio_filename = f"step_{step_idx}{ext}"
                    with open(session_dir / audio_filename, "wb") as f:
                        f.write(audio_data)
                    result["audio_url"] = f"/audio/{session_id}/{audio_filename}"
                    result.pop("audio", None)  # Remove raw bytes before broadcast

                # 广播 step 事件（扁平化，无 'data' 包装）
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

            def on_phase(msg: str):
                asyncio.run_coroutine_threadsafe(
                    bcast({"type": "reasoning", "content": msg}),
                    asyncio.get_event_loop()
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
