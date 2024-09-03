from __future__ import annotations

import logging
import re
from typing import Union, List

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain.tools import BaseTool  # 导入 BaseTool

from bean.parser.BaseOutputParser import BaseOutputParser
from setting.prompt_Thinking import FORMAT_INSTRUCTIONS

logger = logging.getLogger(__name__)


class StructuredThinkingOutputParser(BaseOutputParser):
    """结构化思维输出解析器。"""

    format_instructions: str = FORMAT_INSTRUCTIONS
    """默认格式说明"""

    tools: list[BaseTool] = []  # BaseTool 对象数组

    def __init__(self, tools: list[BaseTool]):
        super().__init__()
        self.tools = tools

    def get_format_instructions(self) -> str:
        """Returns formatting instructions for the given output parser."""
        return self.format_instructions

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """解析文本以确定是否含有任一工具名称，并进行适当的动作。

        参数:
            text (str): 输入文本。

        返回:
            AgentAction 或 AgentFinish: 根据解析结果返回动作或结束信号。
        """
        # 使用正则表达式检查文本中是否含有工具的名称
        matched_tools = [tool for tool in self.tools if re.search(f"\\b{tool.name}\\b", text)]

        if len(matched_tools) > 1:
            raise OutputParserException(
                f"你尝试与多位专家取得联络, 匹配到的专家名称为：{', '.join(tool.name for tool in matched_tools)}。"
                "请确保只存在一个专家名称。"
            )
        elif not matched_tools:
            raise OutputParserException(
                "响应中未匹配到任何专家名称。"
                f"可联系的专家名称如下：{', '.join(tool.name for tool in self.tools)}。"
                "请确保联络一位专家传递信息。"
            )

        tool_name = matched_tools[0].name

        return AgentAction(tool_name, {}, text)

    def render_text_description_and_args(self, tools: List[BaseTool]) -> str:
        """
        生成工具的名称、描述及参数的纯文本格式描述。

        参数:
            tools (List[BaseTool]): 需要渲染的工具列表。

        返回:
            str: 生成的文本描述。

        输出将采用如下格式:

        """
        expert_strings = []
        for tool in tools:
            description = f"专家名称 :{tool.name} \n详细介绍 : \n{tool.description}"
            expert_strings.append(f"{description}\n")
        return "\n".join(expert_strings)
