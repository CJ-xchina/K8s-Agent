from __future__ import annotations

import json
import logging
import re
from inspect import signature
from typing import  Union, List
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from bean.parser.BaseOutputParser import BaseOutputParser
from langchain_core.tools import BaseTool

from setting.prompt_Action import FORMAT_INSTRUCTIONS

logger = logging.getLogger(__name__)


class StructuredChatOutputParser(BaseOutputParser):
    """Output parser for the structured chat agent."""

    format_instructions: str = FORMAT_INSTRUCTIONS
    """Default formatting instructions"""

    final_action: str = "Final Answer"

    tool_name: str = "action"

    tool_vars: str = "action_input"

    def get_format_instructions(self) -> str:
        """Returns formatting instructions for the given output parser."""
        return self.format_instructions

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        # Check if the response dictionary has exactly the required two keys
        required_keys = {self.tool_name, self.tool_vars}

        try:
            response = json.loads(text, strict=False)
        except json.JSONDecodeError:
            raise OutputParserException(f"无法解析输出的动作: {text}，这是因为你输出的动作不符合要求的格式规范！"
                                        f"你的输出应该是一个完整的JSON, 不允许出现除了Json外的其他内容！"
                                        f"请你详细阅读工具使用说明中的案例并且根据这个正则表达式分析为什么会无法解析到你输出的内容！")

        response_keys = set(response.keys())
        # Check if the required keys are in the response dictionary
        if response_keys != required_keys:
            raise OutputParserException(
                f"无法解析输出的动作: {text}。" +
                f"你输入的Json中，要求的工具名称的 key 应该是 '{self.tool_name}'，"
                f"要求的工具变量名称应该是 '{self.tool_vars}'"

            )
        if response["action"] == self.final_action:
            return AgentFinish({"output": response["action_input"]}, text)
        else:
            return AgentAction(
                response["action"], response.get("action_input", {}), text
            )


    def render_text_description_and_args(self, tools: List[BaseTool]) -> str:
        """
        生成工具的名称、描述及参数的纯文本格式描述。

        参数:
            tools (List[BaseTool]): 需要渲染的工具列表。

        返回:
            str: 生成的文本描述。

        输出将采用如下格式:

        .. code-block:: markdown

            search: This tool is used for search, args: {"query": {"type": "string"}}
            calculator: This tool is used for math, \
    args: {"expression": {"type": "string"}}
        """
        tool_strings = []
        for tool in tools:
            args_schema = str(tool.args)
            if hasattr(tool, "func") and tool.func:
                # 如果工具有相关的函数，则获取其签名
                sig = signature(tool.func)
                description = f"{tool.name}{sig} - {tool.description}"
            else:
                # 如果工具没有相关函数，仅展示名称和描述
                description = f"{tool.name} - {tool.description}"
            tool_strings.append(f"{description}, args: {args_schema}")
        return "\n".join(tool_strings)

    @property
    def _type(self) -> str:
        return "structured_chat"
