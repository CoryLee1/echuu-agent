"""初始化数据库数据"""
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import User, LLMModel, VTuber3DModel, Character, VoiceConfig, UserRole, LLMProvider
from auth.auth import get_password_hash


def init_default_data():
    """初始化默认数据"""
    db = SessionLocal()
    try:
        # 检查是否已初始化
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("ℹ️  默认数据已存在，跳过初始化")
            return
        # 创建默认管理员用户
        admin_password = "admin123"  # 确保是字符串
        try:
            password_hash = get_password_hash(admin_password)
        except Exception as e:
            print(f"⚠️  密码哈希生成失败: {e}")
            # 如果 bcrypt 有问题，使用简单的哈希作为后备（仅用于开发）
            import hashlib
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            print("⚠️  使用 SHA256 作为后备方案（仅开发环境）")
        
        admin = User(
            username="admin",
            email="admin@echuu.local",
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()  # 确保admin.id可用
        print("✅ 创建默认管理员用户: admin / admin123")
        
        # 创建默认LLM模型
        default_llm = db.query(LLMModel).filter(LLMModel.is_default == True).first()
        if not default_llm:
            default_llm = LLMModel(
                name="Claude Sonnet 4",
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-sonnet-4-20250514",
                api_key_env="ANTHROPIC_API_KEY",
                is_default=True,
                config={"temperature": 0.7, "max_tokens": 4096}
            )
            db.add(default_llm)
            print("✅ 创建默认LLM模型")
        
        # 创建备用LLM模型
        openai_model = db.query(LLMModel).filter(LLMModel.model_id == "gpt-4").first()
        if not openai_model:
            openai_model = LLMModel(
                name="GPT-4",
                provider=LLMProvider.OPENAI,
                model_id="gpt-4",
                api_key_env="OPENAI_API_KEY",
                is_default=False,
                config={"temperature": 0.7, "max_tokens": 4096}
            )
            db.add(openai_model)
            print("✅ 创建OpenAI模型")
        
        db.flush()  # 确保LLM模型ID可用
        
        # 创建默认角色（为管理员用户）
        default_characters = [
            {
                "name": "六螺",
                "persona": "性格古怪、碎碎念、情绪丰富的虚拟主播",
                "background": "正在直播间里聊八卦，喜欢和弹幕互动。",
                "voice_name": "Cherry",
            },
            {
                "name": "小梅",
                "persona": "温柔治愈型，喜欢分享生活细节",
                "background": "猫咪爱好者，晚上直播陪伴观众入睡。",
                "voice_name": "Bella",
            },
        ]
        
        for char_data in default_characters:
            existing_char = db.query(Character).filter(
                Character.user_id == admin.id,
                Character.name == char_data["name"]
            ).first()
            
            if not existing_char:
                character = Character(
                    user_id=admin.id,
                    name=char_data["name"],
                    persona=char_data["persona"],
                    background=char_data["background"],
                    default_llm_model_id=default_llm.id if default_llm else None,
                )
                db.add(character)
                db.flush()  # 获取character.id
                
                # 为角色添加默认声音配置
                default_voice = VoiceConfig(
                    character_id=character.id,
                    voice_name=char_data["voice_name"],
                    tts_model="qwen3-tts-flash-realtime",
                    is_default=True,
                    priority=0,
                )
                db.add(default_voice)
                print(f"✅ 创建默认角色: {char_data['name']}")
        
        db.commit()
        print("✅ 数据库初始化完成")
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_default_data()
