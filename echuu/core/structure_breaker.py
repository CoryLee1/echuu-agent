"""
结构破坏器 - 打破AI的完美叙事倾向

核心功能：
1. 删除升华结尾
2. 添加非闭合结尾
3. 在随机位置插入"诶我说到哪了"
4. 检查并打破过于线性的结构
"""

import re
import random
from typing import List


class StructureBreaker:

    SUBLIMATION_PATTERNS_ZH = [
        r"所以说.*?(善意|人生|道理|意义|重要|珍惜)",
        r"(这件事|这个经历|这次)让我(明白|懂得|学会|理解)",
        r"(人与人之间|生活中).*?(美好|善良|温暖)",
        r"希望(大家|你们).*?(也能|都能|记住)",
        r"(最后|总之).*?(感谢|感恩|珍惜)",
        r"这就是.*?的(意义|价值|道理)",
    ]

    SUBLIMATION_PATTERNS_EN = [
        r"(so|and so).*?(lesson|meaning|learned|realized)",
        r"(this (experience|taught|showed) me).*?(important|value|appreciate)",
        r"(in the end|at the end of the day).*?(grateful|thankful|blessed)",
        r"(I hope|hopefully).*?(you (all|guys)|everyone).*?(remember|learn)",
    ]

    NON_CLOSURE_ENDINGS_ZH = [
        ("commercial", [
            "好了不说了，对了今天SC有人问什么来着...",
            "行，说完了。诶刚刚谁发的SC？",
            "就这样，我去看看弹幕说什么",
        ]),
        ("topic_hijack", [
            "好了不说这个了，{next_topic}",
            "算了，说别的，{next_topic}",
            "行了行了，{next_topic}",
        ]),
        ("forgotten", [
            "我本来还想说什么来着...算了想不起来了",
            "后面还有什么来着...不重要了",
            "诶我忘了要说的点了，算了",
        ]),
        ("energy_drop", [
            "行了说太多了，就这样",
            "好累，不说了",
            "差不多就这样吧",
        ]),
        ("distraction", [
            "{pet_name}！...抱歉我们说到哪了，算了不说了",
            "等下有人敲门...好，刚才说到哪，算了就这样吧",
        ]),
        ("simple", [
            "就这样",
            "反正就是这么个事",
            "嗯，就这样",
            "好了",
        ]),
    ]

    NON_CLOSURE_ENDINGS_EN = [
        ("commercial", [
            "anyway, let me check chat real quick...",
            "that's it. oh wait who sent that SC?",
        ]),
        ("topic_hijack", [
            "anyway moving on, {next_topic}",
            "let's talk about something else, {next_topic}",
        ]),
        ("forgotten", [
            "I was gonna say something else but... forgot",
            "what was I gonna add... nevermind",
        ]),
        ("energy_drop", [
            "yeah that's basically it",
            "anyway yeah",
        ]),
        ("simple", [
            "so yeah",
            "that's the story",
            "yeah",
        ]),
    ]

    def __init__(self, digression_db=None):
        self.digression_db = digression_db

    def detect_sublimation(self, text: str, language: str = "zh") -> bool:
        """检测文本是否包含升华"""
        patterns = self.SUBLIMATION_PATTERNS_ZH if language == "zh" else self.SUBLIMATION_PATTERNS_EN
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def remove_sublimation(self, text: str, language: str = "zh") -> str:
        """删除升华部分"""
        patterns = self.SUBLIMATION_PATTERNS_ZH if language == "zh" else self.SUBLIMATION_PATTERNS_EN

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = match.start()
                sentence_start = start
                for i in range(start - 1, -1, -1):
                    if text[i] in "。！？.!?\n":
                        sentence_start = i + 1
                        break

                text = text[:sentence_start].rstrip()
                break

        return text

    def add_non_closure_ending(
        self, text: str, language: str = "zh", character_config: dict = None
    ) -> tuple:
        """
        添加非闭合结尾

        Returns:
            (new_text, ending_type)
        """
        endings = self.NON_CLOSURE_ENDINGS_ZH if language == "zh" else self.NON_CLOSURE_ENDINGS_EN

        ending_type, templates = random.choice(endings)
        template = random.choice(templates)

        if "{pet_name}" in template:
            pet_name = character_config.get("pet_name", "喵") if character_config else "喵"
            template = template.replace("{pet_name}", pet_name)

        if "{next_topic}" in template:
            next_topics = ["我看看弹幕", "聊点别的", "下一个话题", "看看SC"]
            template = template.replace("{next_topic}", random.choice(next_topics))

        text = text.rstrip()
        if text and text[-1] not in "。！？.!?":
            text += "。" if language == "zh" else "."

        return text + template, ending_type

    def insert_thread_loss(self, script_lines: List[dict], probability: float = 0.3) -> List[dict]:
        """
        随机插入"丢失思路"的标记

        在某些行的开头添加"诶我说到哪了？对，"
        """
        markers_zh = [
            "诶我说到哪了？对，",
            "刚才说什么来着...对，",
            "不对我要说的是...",
            "等等，我刚想说什么...算了，",
        ]

        markers_en = [
            "wait where was I? right, ",
            "what was I saying... oh yeah, ",
            "no wait I was gonna say... ",
            "hold on what was I... anyway, ",
        ]

        for i, line in enumerate(script_lines):
            if i == 0 or i == len(script_lines) - 1:
                continue

            if line.get("is_digression"):
                continue

            if random.random() < probability:
                language = line.get("language", "zh")
                markers = markers_zh if language == "zh" else markers_en
                marker = random.choice(markers)

                line["text"] = marker + line["text"]
                line["has_thread_loss"] = True

        return script_lines

    def break_structure(
        self, script_lines: List[dict], topic: str, language: str = "zh", character_config: dict = None
    ) -> List[dict]:
        """
        完整的结构破坏流程

        1. 检测并删除升华结尾
        2. 添加非闭合结尾
        3. 可选：注入跑题
        4. 随机插入思路丢失
        """
        if not script_lines:
            return script_lines

        last_line = script_lines[-1]
        text = last_line["text"]

        if self.detect_sublimation(text, language):
            text = self.remove_sublimation(text, language)
            last_line["sublimation_removed"] = True

        text, ending_type = self.add_non_closure_ending(text, language, character_config)
        last_line["text"] = text
        last_line["ending_type"] = ending_type

        has_digression = any(line.get("is_digression") or line.get("has_digression") for line in script_lines)

        if not has_digression and self.digression_db and len(script_lines) > 3:
            inject_idx = random.randint(1, len(script_lines) - 2)
            target_line = script_lines[inject_idx]

            new_text, info = self.digression_db.inject_digression(target_line["text"], topic, language, force=True)
            target_line["text"] = new_text
            target_line["has_digression"] = True
            target_line["digression_info"] = info

        script_lines = self.insert_thread_loss(script_lines, probability=0.2)

        return script_lines
