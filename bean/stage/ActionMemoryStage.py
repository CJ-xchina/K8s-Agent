import json
from typing import List
from langchain.memory import ConversationBufferMemory
from abc import ABC, abstractmethod
from langchain_core.tools import BaseTool
from bean.parser.BaseOutputParser import BaseOutputParser
from bean.stage.ActionStage import ActionStage
from bean.stage.stageType import StageType


class MemoryStrategy(ABC):
    """
    MemoryStrategy 基类定义了用于记忆存储和读取的通用接口。
    """

    @abstractmethod
    def save_memory(self, memory: ConversationBufferMemory, input_str: str, output_str: str):
        """
        保存对话的输入和输出到记忆中。

        Args:
            memory (ConversationBufferMemory): 存储对话历史的记忆对象。
            input_str (str): 用户输入的字符串。
            output_str (str): 模型生成的响应字符串。
        """
        pass

    @abstractmethod
    def load_memory(self, memory: ConversationBufferMemory) -> dict:
        """
        从记忆中加载对话历史。

        Args:
            memory (ConversationBufferMemory): 存储对话历史的记忆对象。

        Returns:
            dict: 包含对话历史的字典。
        """
        pass


class ActionMemoryStage(ActionStage):
    """
    ActionMemoryStage 类用于实现记忆存储和读取功能，并提供接口以获取当前 Stage 类型。

    Attributes:
        memory (ConversationBufferMemory): 用于存储和读取对话历史的记忆对象。
    """

    def __init__(self,
                 prompt: str,
                 tools: List[BaseTool],
                 tool_parser: BaseOutputParser,
                 memory: ConversationBufferMemory,
                 **kwargs):
        """
        初始化 ActionMemoryStage 类。

        Args:
            prompt (str): 用于对话的初始提示字符串。
            tools (List[BaseTool]): 可用工具的列表。
            tool_parser (BaseOutputParser): 用于解析工具操作输出的解析器。
            stage_type (str): 当前 Stage 的类型（例如 "ToolStage" 或 "ThinkingStage"）。
            **kwargs: 其他可选参数，直接传递给父类的 __init__ 方法。
        """
        # 直接传递 kwargs 给父类的 __init__ 方法
        super().__init__(prompt=prompt, tools=tools, tool_parser=tool_parser, **kwargs)
        self.prompt = prompt
        self.tools = tools
        self.tool_parser = tool_parser
        self.memory = memory
        self.stage_type = self.get_stage_type()
        self.memory_strategy = self.get_memory_strategy()

    @abstractmethod
    def get_stage_type(self) -> StageType:
        """
        获取当前 Stage 的类型。

        Returns:
            str: 当前 Stage 的类型（例如 "ToolStage" 或 "ThinkingStage"）。
        """
        pass

    @abstractmethod
    def get_memory_strategy(self) -> MemoryStrategy:
        pass

    def save_memory(self, input_str: str, output_str: str):
        """
        保存对话的输入和输出到记忆中。

        Args:
            input_str (str): 用户输入的字符串。
            output_str (str): 模型生成的响应字符串。
        """
        self.memory_strategy.save_memory(self.memory, input_str, output_str)

    def load_memory(self) -> dict:
        """
        从记忆中加载对话历史。

        Returns:
            dict: 包含对话历史的字典。
        """
        return self.memory_strategy.load_memory(self.memory)

    def _step(self, variables=None):
        """
        调用父类的 _step 方法生成对话输出，并根据输出执行相应的工具操作，返回生成的响应。

        Args:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        Returns:
            str: 生成的响应。
        """
        # 加载记忆
        memory_data = self.load_memory()

        # 结合变量和记忆数据
        if memory_data:
            if variables is None:
                variables = memory_data
            else:
                variables.update(memory_data)

        # 调用父类的 _step 方法获取初步输出
        final_output = super()._step(variables=variables)

        # 保存记忆
        input_str = json.dumps(variables, ensure_ascii=False) if variables else ""
        self.save_memory(input_str, final_output)

        # 返回生成的响应
        return final_output

    def generate_output(self, variables=None) -> str:
        """
        生成对话输出的逻辑（可以在子类中重写该方法）。

        Args:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        Returns:
            str: 生成的对话输出。
        """
        # 具体的生成逻辑应在子类中实现
        raise NotImplementedError("generate_output method needs to be implemented by the subclass.")
