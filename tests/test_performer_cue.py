"""
PerformerCue 单元测试
"""

import pytest
import json

from echuu.core.performer_cue import (
    PerformerCue,
    EmotionCue,
    GestureCue,
    LookCue,
    BlinkCue,
    LipsyncCue,
    CameraCue,
    EmotionKey,
    LookTarget,
    BlinkMode,
    infer_emotion_from_text,
    EMOTION_KEYWORD_MAP,
)
from echuu.vrm.mapper import VRMExpressionMapper, VRMVersion
from echuu.vrm.presets import (
    GESTURE_PRESETS,
    GestureCategory,
    get_gesture_by_emotion,
    get_gesture_for_stage,
)


class TestEmotionCue:
    """EmotionCue 测试"""

    def test_creation(self):
        cue = EmotionCue(key=EmotionKey.HAPPY, intensity=0.8)
        assert cue.key == EmotionKey.HAPPY
        assert cue.intensity == 0.8
        assert cue.attack == 0.2
        assert cue.release == 0.3

    def test_intensity_clamping(self):
        cue = EmotionCue(key=EmotionKey.ANGRY, intensity=1.5)
        assert cue.intensity == 1.0

        cue2 = EmotionCue(key=EmotionKey.SAD, intensity=-0.5)
        assert cue2.intensity == 0.0

    def test_string_key_conversion(self):
        cue = EmotionCue(key="happy", intensity=0.7)
        assert cue.key == EmotionKey.HAPPY

    def test_to_dict(self):
        cue = EmotionCue(key=EmotionKey.SURPRISED, intensity=0.9)
        d = cue.to_dict()
        assert d["key"] == "surprised"
        assert d["intensity"] == 0.9


class TestGestureCue:
    """GestureCue 测试"""

    def test_creation(self):
        cue = GestureCue(clip="emote_nod", weight=0.8, duration=1.0)
        assert cue.clip == "emote_nod"
        assert cue.weight == 0.8
        assert cue.loop is False

    def test_to_dict(self):
        cue = GestureCue(clip="talk_gesture_big", duration=2.0, loop=True)
        d = cue.to_dict()
        assert d["clip"] == "talk_gesture_big"
        assert d["loop"] is True


class TestLookCue:
    """LookCue 测试"""

    def test_enum_target(self):
        cue = LookCue(target=LookTarget.CAMERA)
        assert cue.target == LookTarget.CAMERA

    def test_string_target_conversion(self):
        cue = LookCue(target="chat")
        assert cue.target == LookTarget.CHAT

    def test_tuple_target(self):
        cue = LookCue(target=(0.5, 0.3))
        assert cue.target == (0.5, 0.3)

    def test_to_dict(self):
        cue = LookCue(target=LookTarget.DOWN, strength=0.6)
        d = cue.to_dict()
        assert d["target"] == "down"
        assert d["strength"] == 0.6


class TestPerformerCue:
    """PerformerCue 测试"""

    def test_neutral_factory(self):
        cue = PerformerCue.neutral()
        assert cue.emotion.key == EmotionKey.NEUTRAL
        assert cue.look.target == LookTarget.CAMERA
        assert cue.blink.mode == BlinkMode.AUTO
        assert cue.lipsync.enabled is True

    def test_full_cue_creation(self):
        cue = PerformerCue(
            emotion=EmotionCue(key=EmotionKey.HAPPY, intensity=0.8),
            gesture=GestureCue(clip="react_laugh", duration=1.5),
            look=LookCue(target=LookTarget.CAMERA),
            blink=BlinkCue(mode=BlinkMode.AUTO),
            lipsync=LipsyncCue(enabled=True),
            beat=0.5,
            pause=0.3,
        )
        assert cue.emotion.key == EmotionKey.HAPPY
        assert cue.gesture.clip == "react_laugh"
        assert cue.beat == 0.5
        assert cue.pause == 0.3

    def test_to_dict(self):
        cue = PerformerCue(
            emotion=EmotionCue(key=EmotionKey.SAD, intensity=0.6),
            look=LookCue(target=LookTarget.DOWN),
        )
        d = cue.to_dict()
        assert "emotion" in d
        assert d["emotion"]["key"] == "sad"
        assert "look" in d
        assert d["look"]["target"] == "down"
        assert "gesture" not in d  # None values not included

    def test_to_json(self):
        cue = PerformerCue(
            emotion=EmotionCue(key=EmotionKey.HAPPY, intensity=0.9),
        )
        json_str = cue.to_json()
        parsed = json.loads(json_str)
        assert parsed["emotion"]["key"] == "happy"

    def test_from_dict(self):
        data = {
            "emotion": {"key": "angry", "intensity": 0.7, "attack": 0.1, "release": 0.2},
            "gesture": {"clip": "pose_angry", "weight": 1.0, "duration": 1.5, "loop": True},
            "look": {"target": "camera", "strength": 0.8},
            "beat": 0.25,
        }
        cue = PerformerCue.from_dict(data)
        assert cue.emotion.key == EmotionKey.ANGRY
        assert cue.emotion.intensity == 0.7
        assert cue.gesture.clip == "pose_angry"
        assert cue.gesture.loop is True
        assert cue.look.target == LookTarget.CAMERA
        assert cue.beat == 0.25

    def test_roundtrip(self):
        """测试 to_dict -> from_dict 往返一致性"""
        original = PerformerCue(
            emotion=EmotionCue(key=EmotionKey.SURPRISED, intensity=0.85),
            gesture=GestureCue(clip="react_surprised", duration=0.8),
            look=LookCue(target=LookTarget.UP, strength=0.7),
            blink=BlinkCue(mode=BlinkMode.HOLD),
            lipsync=LipsyncCue(enabled=True),
            camera=CameraCue(preset="closeup", zoom=1.2),
            pause=0.5,
        )
        d = original.to_dict()
        restored = PerformerCue.from_dict(d)

        assert restored.emotion.key == original.emotion.key
        assert restored.emotion.intensity == original.emotion.intensity
        assert restored.gesture.clip == original.gesture.clip
        assert restored.look.target == original.look.target
        assert restored.blink.mode == original.blink.mode
        assert restored.camera.preset == original.camera.preset
        assert restored.pause == original.pause


class TestInferEmotion:
    """infer_emotion_from_text 测试"""

    def test_happy_keywords(self):
        cue = infer_emotion_from_text("今天好开心啊！")
        assert cue.key == EmotionKey.HAPPY

    def test_angry_keywords(self):
        cue = infer_emotion_from_text("真是太生气了")
        assert cue.key == EmotionKey.ANGRY

    def test_sad_keywords(self):
        cue = infer_emotion_from_text("有点难过...")
        assert cue.key == EmotionKey.SAD

    def test_surprised_keywords(self):
        cue = infer_emotion_from_text("我当时就震惊了！")
        assert cue.key == EmotionKey.SURPRISED

    def test_neutral_default(self):
        cue = infer_emotion_from_text("今天天气不错")
        assert cue.key == EmotionKey.NEUTRAL

    def test_exclamation_intensity(self):
        cue = infer_emotion_from_text("太棒了！！")
        assert cue.intensity >= 0.8

    def test_ellipsis_intensity(self):
        cue = infer_emotion_from_text("嗯...让我想想...")
        assert cue.intensity <= 0.6

    def test_stage_modifier(self):
        cue_climax = infer_emotion_from_text("开心", stage="Climax")
        cue_resolution = infer_emotion_from_text("开心", stage="Resolution")
        assert cue_climax.intensity > cue_resolution.intensity


class TestVRMMapper:
    """VRMExpressionMapper 测试"""

    def test_vrm0_mapping(self):
        mapper = VRMExpressionMapper(version=VRMVersion.VRM0)
        result = mapper.map_emotion(EmotionKey.HAPPY, 0.8)
        assert result["blendShape"] == "Joy"
        assert result["weight"] == 0.8

    def test_vrm1_mapping(self):
        mapper = VRMExpressionMapper(version=VRMVersion.VRM1)
        result = mapper.map_emotion(EmotionKey.HAPPY, 0.8)
        assert result["blendShape"] == "happy"

    def test_custom_mapping(self):
        mapper = VRMExpressionMapper(
            version=VRMVersion.VRM1,
            custom_mappings={"happy": "CustomHappy"},
        )
        result = mapper.map_emotion(EmotionKey.HAPPY, 1.0)
        assert result["blendShape"] == "CustomHappy"

    def test_viseme_mapping(self):
        mapper = VRMExpressionMapper(version=VRMVersion.VRM1)
        result = mapper.map_viseme("aa", 0.9)
        assert result["blendShape"] == "aa"
        assert result["weight"] == 0.9

    def test_to_vrm_command(self):
        mapper = VRMExpressionMapper(version=VRMVersion.VRM1)
        cmd = mapper.to_vrm_command(EmotionKey.ANGRY, intensity=0.7)
        assert cmd["type"] == "expression"
        assert cmd["blendShape"] == "angry"
        assert cmd["fadeIn"] == 0.2
        assert cmd["version"] == "vrm1"


class TestGesturePresets:
    """动作预设测试"""

    def test_presets_exist(self):
        assert len(GESTURE_PRESETS) >= 15

    def test_preset_structure(self):
        for name, preset in GESTURE_PRESETS.items():
            assert preset.name == name
            assert preset.category in GestureCategory
            assert preset.duration > 0
            assert len(preset.compatible_emotions) > 0

    def test_get_gesture_by_emotion(self):
        gesture = get_gesture_by_emotion("happy")
        assert gesture is not None
        assert "happy" in gesture.compatible_emotions

    def test_get_gesture_for_stage(self):
        gesture = get_gesture_for_stage("Climax", "surprised")
        assert gesture is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
