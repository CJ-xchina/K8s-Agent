import re
from typing import List, Callable

from langchain_core.agents import AgentAction
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool

from bean.parser.BaseOutputParser import BaseOutputParser
from setting.prompt_Extract import FORMAT_INSTRUCTIONS


class StructuredConclusionOutputParser(BaseOutputParser):
    """
    解析模型输出的结论，使用正则表达式来匹配指定的字符串数组中的一个（忽略大小写）。
    """

    def get_format_instructions(self) -> str:
        template = FORMAT_INSTRUCTIONS

        # 每次动态调用 pattern_func 来获取最新的 patterns
        prompt = PromptTemplate(
            input_variables=["tools_names"],
            template=template
        )

        prompt_str = prompt.format(tools_names=', '.join(self.patterns),)
        return prompt_str

    def render_text_description_and_args(self, tools: List[BaseTool]) -> str:
        return ""

    def __init__(self, pattern_func: Callable[[], List[str]]):
        """
        初始化解析器，传入一个函数，该函数返回一个包含多个字符串的数组用于匹配。

        参数:
            pattern_func (Callable[[], List[str]]): 返回字符串数组的函数。
        """
        self._pattern_func = pattern_func  # 存储函数引用

    @property
    def patterns(self) -> List[str]:
        """
        每次访问时，动态调用函数以获取最新的 patterns。
        """
        return self._pattern_func()

    def parse(self, text: str) -> AgentAction:
        """
        解析传入的文本，并确保匹配的字符串在 patterns 数组中是唯一的（忽略大小写）。

        参数:
            text (str): 模型的输出文本，要求解析其中的结论。

        返回:
            str: 匹配的唯一结果。

        异常:
            OutputParserException: 如果匹配到0个或多个结果，则抛出异常。
        """
        matches = []

        # 动态调用 pattern_func 获取最新的 patterns
        current_patterns = self.patterns

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
