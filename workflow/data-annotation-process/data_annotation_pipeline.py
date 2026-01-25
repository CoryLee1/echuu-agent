"""
VTuber数据标注Pipeline
将原始JSONL数据转换为echuu notebook可用的annotated格式
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
from pathlib import Path

# ============================================
# Schema定义（与echuu notebook保持一致）
# ============================================

class AttentionFocus(str, Enum):
    SELF = "self"           # 自言自语/内心独白/讲自己的事
    AUDIENCE = "audience"   # 直接对观众说话（你们、大家）
    SPECIFIC = "specific"   # 回应特定观众（读SC、点名）
    CONTENT = "content"     # 专注于内容（逗猫、看画面）
    META = "meta"           # 谈论直播本身


class SpeechAct(str, Enum):
    NARRATE = "narrate"     # 叙事：讲故事、描述经历
    OPINE = "opine"         # 表态：发表观点、评价
    RESPOND = "respond"     # 回应：回答问题、接梗
    ELICIT = "elicit"       # 引出：提问、抛梗、邀请互动
    PIVOT = "pivot"         # 转折：话题转换、承上启下
    BACKCHANNEL = "backchannel"  # 填充：语气词、思考、过渡


class Trigger(str, Enum):
    SC = "sc"               # SC/打赏触发
    DANMAKU = "danmaku"     # 弹幕触发
    SELF = "self"           # 自发（无外部触发）
    CONTENT = "content"     # 内容触发（猫动了、画面变化）
    PRIOR = "prior"         # 承接上文


@dataclass
class Segment:
    """标注后的segment"""
    id: str
    start_time: float
    end_time: float
    text: str
    attention_focus: str
    speech_act: str
    trigger: str
    catchphrase: Optional[str] = None
    emotion_shift: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "attention_focus": self.attention_focus,
            "speech_act": self.speech_act,
            "trigger": self.trigger,
            "catchphrase": self.catchphrase,
            "emotion_shift": self.emotion_shift
        }


@dataclass
class AnnotatedClip:
    """标注后的clip"""
    clip_id: str
    source: str
    language: str
    duration: float
    title: str
    skeleton: str
    catchphrases: List[str]
    segments: List[Segment]
    notes: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "source": self.source,
            "language": self.language,
            "duration": self.duration,
            "title": self.title,
            "skeleton": self.skeleton,
            "catchphrases": self.catchphrases,
            "segments": [s.to_dict() for s in self.segments],
            "notes": self.notes
        }


# ============================================
# 数据加载
# ============================================

def load_raw_clips(jsonl_path: str) -> List[Dict]:
    """加载原始JSONL数据"""
    clips = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                clips.append(json.loads(line))
    return clips


def extract_catchphrases(habit_str: str) -> List[str]:
    """从notes.habit字符串中提取口癖列表"""
    if not habit_str:
        return []
    # 匹配引号内的内容
    pattern = r'["""]([^"""]+)["""]'
    matches = re.findall(pattern, habit_str)
    # 清理并去重
    catchphrases = []
    for m in matches:
        clean = m.strip()
        if clean and clean not in catchphrases:
            catchphrases.append(clean)
    return catchphrases


def extract_skeleton(structure_str: str) -> str:
    """提取叙事骨架"""
    if not structure_str:
        return ""
    # 已经是箭头格式的直接返回
    if "→" in structure_str or "->" in structure_str:
        return structure_str.replace("->", "→")
    return structure_str


def infer_trigger_from_notes(notes: Dict) -> str:
    """从notes推断主要触发类型"""
    trigger_text = notes.get("trigger", "").lower()
    
    if any(kw in trigger_text for kw in ["sc", "打赏", "礼物", "superchat"]):
        return "sc"
    elif any(kw in trigger_text for kw in ["弹幕", "观众", "问题", "提问", "chat"]):
        return "danmaku"
    elif any(kw in trigger_text for kw in ["宠物", "猫", "狗", "画面", "内容"]):
        return "content"
    elif any(kw in trigger_text for kw in ["自发", "闲聊", "回忆", "分享"]):
        return "self"
    else:
        return "self"


# ============================================
# LLM标注Prompt
# ============================================

SEGMENT_ANNOTATION_PROMPT = '''你是一个专业的直播内容分析师。请对以下直播切片进行segment级别的标注。

## 切片信息
- 标题: {title}
- 语言: {language}
- 时长: {duration}秒
- 主要触发: {main_trigger}
- 叙事结构: {skeleton}
- 口癖: {catchphrases}

## 转录文本
```
{transcript}
```

## 原始备注
{notes}

## 标注维度

### 1. attention_focus（注意力指向）
- `self`: 自言自语/讲自己的事/内心独白
- `audience`: 直接对观众说话（你们、大家、chat）
- `specific`: 回应特定观众（读SC、点名、感谢xxx）
- `content`: 专注于内容（逗猫、看画面、描述场景）
- `meta`: 谈论直播本身（今天播多久、设备问题）

### 2. speech_act（话语行为）
- `narrate`: 叙事，讲故事、描述经历、回忆
- `opine`: 表态，发表观点、评价、建议
- `respond`: 回应，回答问题、接梗、反驳
- `elicit`: 引出，提问、抛梗、邀请互动
- `pivot`: 转折，话题转换、承上启下
- `backchannel`: 填充，语气词、思考、"嗯"/"uhm"

### 3. trigger（触发源）
- `sc`: SC/打赏触发
- `danmaku`: 弹幕触发
- `self`: 自发（无外部触发，自己想起来的）
- `content`: 内容触发（画面变化、宠物动作）
- `prior`: 承接上文（延续前一个segment）

## 切分原则

1. **语义完整**：每个segment应该是一个语义完整的单元
2. **时长合理**：通常5-30秒，过长需要切分
3. **变化敏感**：当attention_focus或speech_act明显变化时切分
4. **保持简洁**：一个2分钟切片通常5-10个segment

## 输出格式

请输出JSON格式：

```json
{{
  "segments": [
    {{
      "id": "seg_01",
      "start_time": 0,
      "end_time": 15,
      "text": "完整的segment文本",
      "attention_focus": "specific",
      "speech_act": "respond",
      "trigger": "sc",
      "catchphrase": "对吧",
      "emotion_shift": false
    }}
  ],
  "analysis_notes": "简短分析备注"
}}
```

只输出JSON，不要其他内容。'''


def create_annotation_prompt(clip: Dict) -> str:
    """为单个clip创建标注prompt"""
    # 格式化转录文本
    transcript_lines = []
    for item in clip.get("transcript", []):
        t = item.get("t", 0)
        if t is not None:
            minutes = int(t // 60)
            seconds = int(t % 60)
            transcript_lines.append(f"{minutes}:{seconds:02d} {item.get('text', '')}")
        else:
            transcript_lines.append(f"-- {item.get('text', '')}")
    
    transcript = "\n".join(transcript_lines)
    
    # 提取信息
    notes = clip.get("notes", {})
    catchphrases = extract_catchphrases(notes.get("habit", ""))
    skeleton = extract_skeleton(notes.get("structure", ""))
    main_trigger = infer_trigger_from_notes(notes)
    
    # 格式化notes
    notes_str = "\n".join([f"- {k}: {v}" for k, v in notes.items()])
    
    return SEGMENT_ANNOTATION_PROMPT.format(
        title=clip.get("title", ""),
        language=clip.get("language", "zh"),
        duration=clip.get("duration", 0),
        main_trigger=main_trigger,
        skeleton=skeleton,
        catchphrases=catchphrases,
        transcript=transcript,
        notes=notes_str
    )


# ============================================
# LLM调用
# ============================================

def call_llm_for_annotation(prompt: str, client=None, model: str = "claude-3-haiku-20240307") -> Dict:
    """
    调用LLM进行标注
    
    Args:
        prompt: 标注prompt
        client: Anthropic/OpenAI client
        model: 模型名称
    
    Returns:
        解析后的JSON结果
    """
    if client is None:
        print("⚠️ 无API client，返回空结果")
        return {"segments": [], "analysis_notes": "需要配置API"}
    
    try:
        # Anthropic API
        if hasattr(client, 'messages'):
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        # OpenAI API
        else:
            response = client.chat.completions.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
        
        # 提取JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
        
        return json.loads(json_str.strip())
        
    except Exception as e:
        print(f"LLM调用错误: {e}")
        return {"segments": [], "analysis_notes": f"错误: {e}"}


# ============================================
# 数据转换Pipeline
# ============================================

def annotate_clip(clip: Dict, client=None, model: str = "claude-3-haiku-20240307") -> AnnotatedClip:
    """
    标注单个clip
    
    Args:
        clip: 原始clip数据
        client: LLM client
        model: 模型名称
    
    Returns:
        标注后的AnnotatedClip
    """
    notes = clip.get("notes", {})
    catchphrases = extract_catchphrases(notes.get("habit", ""))
    skeleton = extract_skeleton(notes.get("structure", ""))
    
    # 创建prompt并调用LLM
    prompt = create_annotation_prompt(clip)
    result = call_llm_for_annotation(prompt, client, model)
    
    # 转换segments
    segments = []
    for i, seg_data in enumerate(result.get("segments", [])):
        segment = Segment(
            id=seg_data.get("id", f"seg_{i+1:02d}"),
            start_time=seg_data.get("start_time", 0),
            end_time=seg_data.get("end_time", 0),
            text=seg_data.get("text", ""),
            attention_focus=seg_data.get("attention_focus", "self"),
            speech_act=seg_data.get("speech_act", "narrate"),
            trigger=seg_data.get("trigger", "self"),
            catchphrase=seg_data.get("catchphrase"),
            emotion_shift=seg_data.get("emotion_shift", False)
        )
        segments.append(segment)
    
    # 如果LLM没有返回segments，创建一个默认的
    if not segments:
        transcript = clip.get("transcript", [])
        if transcript:
            # 将整个transcript作为一个segment
            full_text = " ".join([t.get("text", "") for t in transcript])
            start_time = transcript[0].get("t", 0) or 0
            end_time = transcript[-1].get("t", 0) or clip.get("duration", 0)
            
            segments.append(Segment(
                id="seg_01",
                start_time=start_time,
                end_time=end_time,
                text=full_text[:500] + "..." if len(full_text) > 500 else full_text,
                attention_focus="self",
                speech_act="narrate",
                trigger=infer_trigger_from_notes(notes)
            ))
    
    return AnnotatedClip(
        clip_id=clip.get("clip_id", ""),
        source=clip.get("source", ""),
        language=clip.get("language", "zh"),
        duration=clip.get("duration", 0),
        title=clip.get("title", ""),
        skeleton=skeleton,
        catchphrases=catchphrases,
        segments=segments,
        notes=notes
    )


def run_annotation_pipeline(
    input_path: str,
    output_path: str,
    client=None,
    model: str = "claude-sonnet-4-20250514",
    max_clips: int = None,
    verbose: bool = True
) -> List[Dict]:
    """
    运行完整的标注Pipeline
    
    Args:
        input_path: 输入JSONL文件路径
        output_path: 输出JSON文件路径
        client: LLM client
        model: 模型名称
        max_clips: 最大处理clip数量（用于测试）
        verbose: 是否打印进度
    
    Returns:
        标注后的clip列表
    """
    # 加载数据
    if verbose:
        print(f"📂 加载数据: {input_path}")
    
    raw_clips = load_raw_clips(input_path)
    
    if max_clips:
        raw_clips = raw_clips[:max_clips]
    
    if verbose:
        print(f"✅ 加载了 {len(raw_clips)} 个clips")
    
    # 标注
    annotated = []
    for i, clip in enumerate(raw_clips):
        if verbose:
            print(f"\n[{i+1}/{len(raw_clips)}] 标注: {clip.get('title', 'Unknown')[:30]}...")
        
        try:
            annotated_clip = annotate_clip(clip, client, model)
            annotated.append(annotated_clip.to_dict())
            
            if verbose:
                print(f"  ✓ {len(annotated_clip.segments)} segments, skeleton: {annotated_clip.skeleton[:30]}...")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            # 添加一个最小化的标注
            annotated.append({
                "clip_id": clip.get("clip_id", ""),
                "source": clip.get("source", ""),
                "language": clip.get("language", ""),
                "duration": clip.get("duration", 0),
                "title": clip.get("title", ""),
                "skeleton": extract_skeleton(clip.get("notes", {}).get("structure", "")),
                "catchphrases": extract_catchphrases(clip.get("notes", {}).get("habit", "")),
                "segments": [],
                "notes": clip.get("notes", {})
            })
    
    # 保存
    if verbose:
        print(f"\n💾 保存到: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(annotated, f, ensure_ascii=False, indent=2)
    
    if verbose:
        print(f"✅ 完成！共标注 {len(annotated)} 个clips")
    
    return annotated


# ============================================
# 快速转换（不调用LLM）
# ============================================

def quick_convert_without_llm(
    input_path: str,
    output_path: str,
    verbose: bool = True
) -> List[Dict]:
    """
    快速转换数据格式，不调用LLM
    使用启发式规则进行segment切分
    
    适用于：
    1. 快速测试echuu notebook
    2. 没有API key时的fallback
    3. 生成初稿后人工校正
    """
    if verbose:
        print(f"📂 快速转换模式（不调用LLM）")
        print(f"📂 加载数据: {input_path}")
    
    raw_clips = load_raw_clips(input_path)
    
    if verbose:
        print(f"✅ 加载了 {len(raw_clips)} 个clips")
    
    annotated = []
    
    for clip in raw_clips:
        notes = clip.get("notes", {})
        catchphrases = extract_catchphrases(notes.get("habit", ""))
        skeleton = extract_skeleton(notes.get("structure", ""))
        main_trigger = infer_trigger_from_notes(notes)
        
        # 启发式segment切分
        transcript = clip.get("transcript", [])
        segments = []
        
        # 按时间间隔切分（每30秒左右一个segment）
        current_seg_texts = []
        current_seg_start = 0
        last_time = 0
        
        for item in transcript:
            t = item.get("t")
            if t is None:
                t = last_time
            text = item.get("text", "")
            
            # 如果时间跨度超过30秒或文本很长，创建新segment
            if t - current_seg_start > 30 or len(" ".join(current_seg_texts)) > 300:
                if current_seg_texts:
                    seg_text = " ".join(current_seg_texts)
                    # 推断attention和speech_act
                    attention, speech_act = infer_segment_type(seg_text, clip.get("language", "zh"))
                    
                    segments.append({
                        "id": f"seg_{len(segments)+1:02d}",
                        "start_time": current_seg_start,
                        "end_time": t,
                        "text": seg_text,
                        "attention_focus": attention,
                        "speech_act": speech_act,
                        "trigger": main_trigger if len(segments) == 0 else "prior",
                        "catchphrase": find_catchphrase(seg_text, catchphrases),
                        "emotion_shift": False
                    })
                
                current_seg_texts = [text]
                current_seg_start = t
            else:
                current_seg_texts.append(text)
            
            last_time = t
        
        # 处理最后一个segment
        if current_seg_texts:
            seg_text = " ".join(current_seg_texts)
            attention, speech_act = infer_segment_type(seg_text, clip.get("language", "zh"))
            
            segments.append({
                "id": f"seg_{len(segments)+1:02d}",
                "start_time": current_seg_start,
                "end_time": clip.get("duration", last_time),
                "text": seg_text,
                "attention_focus": attention,
                "speech_act": speech_act,
                "trigger": main_trigger if len(segments) == 0 else "prior",
                "catchphrase": find_catchphrase(seg_text, catchphrases),
                "emotion_shift": False
            })
        
        annotated.append({
            "clip_id": clip.get("clip_id", ""),
            "source": clip.get("source", ""),
            "language": clip.get("language", "zh"),
            "duration": clip.get("duration", 0),
            "title": clip.get("title", ""),
            "skeleton": skeleton,
            "catchphrases": catchphrases,
            "segments": segments,
            "notes": notes
        })
    
    # 保存
    if verbose:
        print(f"\n💾 保存到: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(annotated, f, ensure_ascii=False, indent=2)
    
    if verbose:
        total_segments = sum(len(c["segments"]) for c in annotated)
        print(f"✅ 完成！共 {len(annotated)} 个clips, {total_segments} 个segments")
    
    return annotated


def infer_segment_type(text: str, language: str) -> Tuple[str, str]:
    """
    启发式推断segment的attention_focus和speech_act
    """
    text_lower = text.lower()
    
    # 中文关键词
    if language == "zh":
        # attention_focus
        if any(kw in text for kw in ["你们", "大家", "观众", "朋友们", "chat"]):
            attention = "audience"
        elif any(kw in text for kw in ["谢谢", "感谢", "SC", "打赏", "送的"]):
            attention = "specific"
        elif any(kw in text for kw in ["猫", "狗", "宠物", "画面"]):
            attention = "content"
        elif any(kw in text for kw in ["直播", "今天播", "开播", "下播"]):
            attention = "meta"
        else:
            attention = "self"
        
        # speech_act
        if any(kw in text for kw in ["我记得", "那时候", "当时", "以前", "有一次"]):
            speech_act = "narrate"
        elif any(kw in text for kw in ["我觉得", "我认为", "应该", "建议"]):
            speech_act = "opine"
        elif any(kw in text for kw in ["？", "吗", "呢", "什么"]) and len(text) < 50:
            speech_act = "elicit"
        elif any(kw in text for kw in ["对", "是的", "没错", "确实"]):
            speech_act = "respond"
        elif any(kw in text for kw in ["说到", "话说", "然后", "接下来"]):
            speech_act = "pivot"
        else:
            speech_act = "narrate"
    
    # 英文关键词
    else:
        # attention_focus
        if any(kw in text_lower for kw in ["you guys", "chat", "everyone", "y'all"]):
            attention = "audience"
        elif any(kw in text_lower for kw in ["thank", "thanks", "appreciate", "superchat"]):
            attention = "specific"
        elif any(kw in text_lower for kw in ["cat", "dog", "pet", "screen"]):
            attention = "content"
        elif any(kw in text_lower for kw in ["stream", "streaming", "today's"]):
            attention = "meta"
        else:
            attention = "self"
        
        # speech_act
        if any(kw in text_lower for kw in ["i remember", "back then", "when i was", "one time"]):
            speech_act = "narrate"
        elif any(kw in text_lower for kw in ["i think", "i believe", "should", "i feel like"]):
            speech_act = "opine"
        elif "?" in text and len(text) < 100:
            speech_act = "elicit"
        elif any(kw in text_lower for kw in ["yeah", "yes", "exactly", "right"]):
            speech_act = "respond"
        elif any(kw in text_lower for kw in ["anyway", "so", "speaking of", "next"]):
            speech_act = "pivot"
        else:
            speech_act = "narrate"
    
    return attention, speech_act


def find_catchphrase(text: str, catchphrases: List[str]) -> Optional[str]:
    """查找文本中出现的口癖"""
    for cp in catchphrases:
        if cp in text:
            return cp
    return None


# ============================================
# 命令行入口
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VTuber数据标注Pipeline")
    parser.add_argument("--input", "-i", required=True, help="输入JSONL文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出JSON文件路径")
    parser.add_argument("--quick", action="store_true", help="快速模式（不调用LLM）")
    parser.add_argument("--max-clips", type=int, help="最大处理clip数量")
    parser.add_argument("--api-key", help="LLM API Key")
    parser.add_argument("--model", default="claude-3-haiku-20240307", help="LLM模型")
    
    args = parser.parse_args()
    
    if args.quick:
        quick_convert_without_llm(args.input, args.output)
    else:
        client = None
        if args.api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=args.api_key)
            except ImportError:
                print("需要安装anthropic: pip install anthropic")
        
        run_annotation_pipeline(
            args.input,
            args.output,
            client=client,
            model=args.model,
            max_clips=args.max_clips
        )
