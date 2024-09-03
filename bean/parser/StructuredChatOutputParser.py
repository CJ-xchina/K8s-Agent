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


class StructuredChatOutputParserWithRetries(AgentOutputParser):
    """Output parser with retries for the structured chat agent."""

    base_parser: AgentOutputParser = Field(default_factory=StructuredChatOutputParser)
    """The base parser to use."""
    output_fixing_parser: Optional[OutputFixingParser] = None
    """The output fixing parser to use."""

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            if self.output_fixing_parser is not None:
                parsed_obj: Union[AgentAction, AgentFinish] = (
                    self.output_fixing_parser.parse(text)
                )
            else:
                parsed_obj = self.base_parser.parse(text)
            return parsed_obj
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @classmethod
    def from_llm(
            cls,
            llm: Optional[BaseLanguageModel] = None,
            base_parser: Optional[StructuredChatOutputParser] = None,
    ) -> StructuredChatOutputParserWithRetries:
        if llm is not None:
            base_parser = base_parser or StructuredChatOutputParser()
            output_fixing_parser: OutputFixingParser = OutputFixingParser.from_llm(
                llm=llm, parser=base_parser
            )
            return cls(output_fixing_parser=output_fixing_parser)
        elif base_parser is not None:
            return cls(base_parser=base_parser)
        else:
            return cls()

    @property
    def _type(self) -> str:
        return "structured_chat_with_retries"


def main():
    # 实例化一个StructuredChatOutputParser对象
    parser = StructuredChatOutputParser()

    # 传入的字符串
    text = """
Thought: 根据先前的查询结果，Pod 'k8s-test-1-64ddfdff5d-6t7m6' 处于 "Failed" 状态，并且容器状态中的 ‘exit_code’ 为 137。这通常表明某种错误导致容器退出执行。尽管未能直接查看日志，但从容器的状态信息推断可能的错误可能是由于内部处理逻辑出现问题所致。因此，下一步我们主要基于当前的信息与已观察到的数据进行总结性判断和分析。
Action:
```json
{
  "action": "Final Answer",
  "action_input": ""
}
```
    """

    # 调用parse方法解析传入的字符串
    result = parser.parse(text)

    # 打印解析结果
    if isinstance(result, AgentAction):
        print("Action:", result.tool)
        print("Action Input:", result.tool_input)
    elif isinstance(result, AgentFinish):
        print("Final Output:", result.return_values["output"])


if __name__ == "__main__":
    main()
