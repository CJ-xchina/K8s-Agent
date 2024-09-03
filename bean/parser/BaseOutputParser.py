from abc import ABC, abstractmethod
from typing import List, Union
from langchain.tools import BaseTool
from langchain_core.agents import AgentAction, AgentFinish


class BaseOutputParser(ABC):
    """基类输出解析器，提供解析输出的接口。"""

    @abstractmethod
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """
        解析文本以确定是否含有任一工具名称，并进行适当的动作。

        参数:
            text (str): 输入文本。

        返回:
            AgentAction 或 AgentFinish: 根据解析结果返回动作或结束信号。
        """
        pass

    @abstractmethod
    def get_format_instructions(self) -> str:
        """
        返回给定输出解析器的格式化指令。

        返回:
            str: 格式化指令。
        """
        pass

    @abstractmethod
    def render_text_description_and_args(self, tools: List[BaseTool]) -> str:
        """
        生成工具的名称、描述及参数的纯文本格式描述。

        参数:
            tools (List[BaseTool]): 需要渲染的工具列表。

        返回:
            str: 生成的文本描述。
        """
        pass
