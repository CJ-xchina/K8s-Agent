import re
from typing import List

from langchain_core.agents import AgentAction
from langchain_core.exceptions import OutputParserException
from langchain_core.tools import BaseTool

from bean.parser.BaseOutputParser import BaseOutputParser


class StructuredConclusionOutputParser(BaseOutputParser):
    """
    解析模型输出的结论，使用正则表达式来匹配指定的字符串数组中的一个（忽略大小写）。
    """

    def get_format_instructions(self) -> str:
        pass

    def render_text_description_and_args(self, tools: List[BaseTool]) -> str:
        return ""

    def __init__(self):
        pass

    def parse(self, text: str, patterns=None) -> AgentAction:
        matches = []

        # 动态调用 pattern_func 获取最新的 patterns
        current_patterns = patterns

        # 遍历 pattern 数组，使用正则表达式查找匹配（忽略大小写）
        for pattern in current_patterns:
            if re.search(re.escape(pattern), text, re.IGNORECASE):
                matches.append(pattern)

        # 如果没有匹配到结果，或者匹配到多个结果，抛出异常
        if len(matches) == 0:
            raise OutputParserException(
                f"无法解析输出: {text}。没有匹配到任何指定的模式。\n"
                f"可匹配的字符串包括: {', '.join(current_patterns)}, 你输出的内容必须要包含其中之一"
            )
        elif len(matches) > 1:
            raise OutputParserException(
                f"解析错误: {text}。匹配到多个模式: {matches}。\n"
                f"可匹配的字符串包括: {', '.join(current_patterns)},  你输出的内容必须要包含其中之一"
            )

        # 返回唯一的匹配
        match_str = matches[0]

        return AgentAction(tool=match_str, tool_input=match_str, log="")
