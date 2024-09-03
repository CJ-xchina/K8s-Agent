from __future__ import annotations

import json
import logging
import re
from typing import Optional, Pattern, Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseLanguageModel
from langchain_core.pydantic_v1 import Field

from langchain.agents.agent import AgentOutputParser
from langchain.output_parsers import OutputFixingParser

from setting.prompt_Action import FORMAT_INSTRUCTIONS

logger = logging.getLogger(__name__)


class StructuredChatOutputParser(AgentOutputParser):
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

    @property
    def _type(self) -> str:
        return "structured_chat"


