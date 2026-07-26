"""P0 回归锁：prompt 模板里不得出现「可被逐字复述的例句」。

泄漏机制：qwen 这类指令跟随较弱的模型无法区分「这是规则说明」和「这是可以照抄的
台词」。凡是被引号/角括号括起来的自然语言（正面例句、反面例句、散文式 JSON 占位符），
都可能原样出现在播出去的台词里——"不准说 X" 在注意力上等价于给 X 加权。

约束写法：规则描述类别，不给样本；JSON schema 的 value 位置一律用 <描述> 占位符。

覆盖 echuu 全部生成类 prompt 模板。
"""
from __future__ import annotations

import re

from echuu.core.persona_analyst import _PROMPT as ANALYST_PROMPT
from echuu.core.persona_expander import _PROMPT as EXPANDER_PROMPT
from echuu.generators.script_writer import _PROMPT_TEMPLATE as WRITER_PROMPT
from echuu.live.danmaku_interleave import _PROMPT as DANMAKU_PROMPT, _QUIP_PROMPT
from echuu.live.response_generator import DanmakuResponseGenerator
from echuu.modes.reaction import _SCRIPT_PROMPT as REACTION_SCRIPT_PROMPT
from echuu.modes.rundown import (
    _CLOSING_PROMPT,
    _GAG_RECALL_RULE,
    _OPENING_PROMPT,
)
from echuu.modes.singing import _MURMUR_PROMPT

ALL_TEMPLATES = {
    "persona_analyst": ANALYST_PROMPT,
    "persona_expander": EXPANDER_PROMPT,
    "script_writer": WRITER_PROMPT,
    "danmaku_interleave": DANMAKU_PROMPT,
    "danmaku_quip": _QUIP_PROMPT,
    "response_generator": DanmakuResponseGenerator.RESPONSE_PROMPT,
    "rundown_opening": _OPENING_PROMPT,
    "rundown_closing": _CLOSING_PROMPT,
    "rundown_gag_recall": _GAG_RECALL_RULE,
    "reaction_script": REACTION_SCRIPT_PROMPT,
    "singing_murmur": _MURMUR_PROMPT,
}

_QUOTED = re.compile(r'[“"「『\'](.{2,60}?)[”"」』\']')
_CJK = re.compile(r"[一-鿿぀-ヿ]")
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def _quotable_literals(template: str) -> list[str]:
    """引号里的自然语言 = 模型可能逐字复述的东西。

    放行三类非台词内容：JSON 字段名（引号后紧跟冒号）、纯标识符/枚举值、
    以及 <...> 形式的占位符与含 {} / | 的 schema 片段。
    """
    hits: list[str] = []
    for match in _QUOTED.finditer(template):
        span = match.group(1).strip()
        tail = template[match.end():match.end() + 1]
        if tail == ":":                                   # JSON key
            continue
        if _IDENTIFIER.match(span):                       # 字段名 / continue 之类枚举值
            continue
        if span.startswith("<") or "|" in span or "{" in span:
            continue
        if not _CJK.search(span) and not re.search(r"[A-Za-z]{3}", span):
            continue
        hits.append(span)
    return hits


def test_prompts_carry_no_quotable_examples():
    offenders = {
        name: literals
        for name, template in ALL_TEMPLATES.items()
        if (literals := _quotable_literals(template))
    }
    assert not offenders, f"prompt 模板里仍有可复述例句: {offenders}"


def test_response_prompt_drops_fabricated_viewer_names():
    """最脏的一处：泄漏出去就是对着观众喊「小明」「John」。"""
    prompt = DanmakuResponseGenerator.RESPONSE_PROMPT
    for name in ("小明", "John", "Johnさん"):
        assert name not in prompt


def test_rundown_prompts_drop_broadcast_cliches():
    """反面例句本身就是模型最爱说的套话，写进 prompt 等于加权。"""
    for cliche in ("大家好我是AI主播", "欢迎来到直播间", "今天很开心", "感谢大家的陪伴"):
        assert cliche not in _OPENING_PROMPT + _CLOSING_PROMPT


def test_json_schema_values_use_angle_placeholders():
    """schema 的 value 位置若写散文说明，模型会当成示例台词返回。"""
    for name in ("singing_murmur", "reaction_script", "response_generator"):
        template = ALL_TEMPLATES[name]
        for match in re.finditer(r'"[a-z_]+":\s*"([^"]{2,})"', template):
            value = match.group(1)
            if _IDENTIFIER.match(value) or "|" in value or "{" in value:
                continue
            assert value.startswith("<"), f"{name} 的 schema 值未占位符化: {value}"
