"""从 localStorage 迁移角色数据到数据库"""
import sys
import json
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import User, Character, VoiceConfig
from auth.auth import get_password_hash


def migrate_from_localstorage():
    """从 localStorage 迁移数据（需要手动提供数据）"""
    db = SessionLocal()
    try:
        # 获取或创建默认用户
        default_user = db.query(User).filter(User.username == "admin").first()
        if not default_user:
            default_user = User(
                username="admin",
                email="admin@echuu.local",
                password_hash=get_password_hash("admin123"),
                role="admin"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        
        # 提示用户提供localStorage数据
        print("=" * 60)
        print("localStorage 数据迁移工具")
        print("=" * 60)
        print("\n请提供 localStorage 中的角色数据（JSON格式）")
        print("在浏览器控制台运行: localStorage.getItem('echuu.characters')")
        print("然后粘贴结果（或直接按回车跳过）:\n")
        
        data_input = input().strip()
        if not data_input:
            print("跳过迁移")
            return
        
        try:
            characters_data = json.loads(data_input)
        except json.JSONDecodeError:
            print("❌ JSON 格式错误")
            return
        
        if not isinstance(characters_data, list):
            print("❌ 数据格式错误，应为数组")
            return
        
        migrated_count = 0
        for char_data in characters_data:
            # 检查角色是否已存在
            existing = db.query(Character).filter(
                Character.user_id == default_user.id,
                Character.name == char_data.get("name")
            ).first()
            
            if existing:
                print(f"⏭️  跳过已存在的角色: {char_data.get('name')}")
                continue
            
            # 创建角色
            character = Character(
                user_id=default_user.id,
                name=char_data.get("name", ""),
                persona=char_data.get("persona", ""),
                background=char_data.get("background", ""),
            )
            db.add(character)
            db.flush()
            
            # 添加默认声音配置（如果原数据没有）
            if character.id:
                default_voice = VoiceConfig(
                    character_id=character.id,
                    voice_name="Cherry",  # 默认声音
                    tts_model="qwen3-tts-flash-realtime",
                    is_default=True,
                    priority=0
                )
                db.add(default_voice)
            
            migrated_count += 1
            print(f"✅ 迁移角色: {char_data.get('name')}")
        
        db.commit()
        print(f"\n✅ 成功迁移 {migrated_count} 个角色")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_from_localstorage()
