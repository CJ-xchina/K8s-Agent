import json
from typing import List, Tuple

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from client.output_parser import StructuredChatOutputParser
from langchain_core.agents import AgentAction

from setting.prompt_Action import NAIVE_FIX, MAIN_PROMPT
from stage.BaseStage import BaseStage
from langchain_core.tools import BaseTool, render_text_description
from collections import Counter

from stage.stageType import StageType
from utils.chat import chat_with_model_str
from utils.tools import extract_tool_signature, execute_action


class ActionStage(BaseStage):
    """
    ActionStage 类用于实现与工具交互的对话逻辑。继承自 BaseStage。

    Attributes:
        tools (List[BaseTool]): 可用工具的列表。
        tool_parser (StructuredChatOutputParser): 用于解析工具操作输出的解析器。
    """

    @staticmethod
    def default_fixing_prompt() -> str:
        return NAIVE_FIX

    @staticmethod
    def default_prompt() -> str:
        return MAIN_PROMPT

    def __init__(self,
                 prompt: str = None,
                 chat_model: BaseChatModel = ChatOpenAI(model="qwen2:7b", base_url="http://localhost:11434/v1",
                                                        api_key="<KEY>"),
                 tools: List[BaseTool] = [],
                 tool_parser: StructuredChatOutputParser = None,
                 self_consistency_times: int = 1,
                 stage_type: StageType = StageType.ACTION,
                 Enable_fixing: bool = False,
                 fixing_model: BaseChatModel = None,
                 fixing_prompt: str = None,
                 fixing_num: int = 3,
                 dynamic_fixing: bool = True):
        """
        初始化 ActionStage 类。

        Args:
            prompt (str): 用于对话的初始提示字符串，如果未指定，调用 default_prompt 函数获取默认值。
            chat_model (BaseChatModel): 用于生成对话的语言模型实例，如果未指定，默认为 None。
            tools (List[BaseTool]): 可用工具的列表，默认为空列表。
            tool_parser (StructuredChatOutputParser): 用于解析工具操作输出的解析器，默认为 None。
            self_consistency_times (int): 自一致性次数，用于模型生成输出的一致性，默认为 1。
            stage_type (StageType): 当前 Stage 的类型，默认为 StageType.ACTION。
            Enable_fixing (bool): 是否启用修复功能，默认为 False。
            fixing_model (BaseChatModel): 用于修复输出的模型，如果未指定，默认使用 chat_model。
            fixing_prompt (str): 用于修复输出的模型的提示词，如果未指定，调用 get_naive_fix 函数获取默认值。
            fixing_num (int): 修复次数，默认为 3。
            dynamic_fixing (bool): 是否启用动态修复，默认为 True。
        """
        self.tools = tools
        self.tool_parser = tool_parser

        if Enable_fixing:
            self.fixing_model = fixing_model if fixing_model is not None else chat_model
            self.fixing_prompt = fixing_prompt if fixing_prompt is not None else self.default_fixing_prompt()
            self.fixing_num = fixing_num
            self.dynamic_fixing = dynamic_fixing

        # 调用父类的初始化函数
        super().__init__(prompt,
                         chat_model if chat_model is not None else BaseChatModel(),
                         stage_type=stage_type,
                         self_consistency_times=self_consistency_times)

    def _initialize_prompt(self, prompt: str) -> PromptTemplate:
        """
        将字符串类型的提示转换为 PromptTemplate 对象。

        参数:
            prompt (str): 原始字符串类型的提示。

        返回:
            PromptTemplate: 转换后的模板对象。

        抛出:
            ValueError: 如果传入的 prompt 为空或不是字符串类型。
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt 必须是一个非空字符串")

        return PromptTemplate.from_template(prompt).partial(
            tools=render_text_description(self.tools),  # 渲染工具描述
            format_instructions=self.__chinese_friendly(  # 处理格式说明
                self.tool_parser.get_format_instructions(),
            )
        )

    def _initialize_fixing_prompt(self, prompt: str, error: str, raw_action: str, cur_action: str) -> PromptTemplate:
        """
        将字符串类型的提示转换为 PromptTemplate 对象，用于修复工具调用错误。

        参数:
            prompt (str): 原始字符串类型的提示。
            error (str): 工具解析过程中遇到的错误描述。
            raw_action (str): 需要修复的调用工具的原始字符串。

        返回:
            PromptTemplate: 转换后的模板对象。

        抛出:
            ValueError: 如果传入的 prompt 为空或不是字符串类型。
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt 必须是一个非空字符串")

        if not isinstance(error, str) or not error.strip():
            raise ValueError("Error 必须是一个非空字符串")

        if not isinstance(raw_action, str) or not raw_action.strip():
            raise ValueError("Raw action 必须是一个非空字符串")

        if not isinstance(cur_action, str) or not raw_action.strip():
            raise ValueError("Raw action 必须是一个非空字符串")

        return PromptTemplate.from_template(prompt).partial(
            tools=render_text_description(self.tools),  # 渲染工具描述
            format_instructions=self.__chinese_friendly(  # 处理格式说明
                self.tool_parser.get_format_instructions(),
            ),
            error=error,
            raw_action=raw_action,
            cur_action=cur_action,
        )

    def select_final_output(self, outputs: list[str]) -> str:
        """
        选择最终输出的方法，基于工具名称和参数的一致性来判断哪个输出最常见。

        Args:
            outputs (list[str]): 所有生成的输出列表。

        Returns:
            str: 选择的最终输出。

        Raises:
            ValueError: 如果输出列表为空。
        """
        if not outputs:
            raise ValueError("输出列表不能为空")

        # 使用自定义逻辑根据工具名称和参数的一致性来分组
        signatures = [extract_tool_signature(output, self.tool_parser) for output in outputs]
        most_common_signature, _ = Counter(signatures).most_common(1)[0]

        # 返回第一个匹配的输出
        for output in outputs:
            if extract_tool_signature(output, self.tool_parser) == most_common_signature:
                print(f"select_final_output: Selected output is '{output}' based on tool consistency.")
                return output

        raise RuntimeError("未能找到匹配的输出。")

    def _step(self, variables=None) -> str:
        """
        调用父类的 _step 方法生成对话输出，并根据输出执行相应的工具操作，返回生成的响应。

        Args:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        Returns:
            str: 工具操作后的结果或语言模型生成的对话响应。
        """
        # 调用父类的 _step 方法获取初步输出
        final_output = super()._step(variables)

        print(f"Final output before tool parsing: {final_output}")

        # 解析生成的响应以确定是否需要调用工具
        action = self.tool_parser.parse(final_output)

        observation = execute_action(tools=self.tools, action=action)

        return observation

    @staticmethod
    def __chinese_friendly(string: str) -> str:
        """处理字符串，使其更加符合中文使用习惯。"""
        lines = string.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('{') and line.endswith('}'):
                try:
                    lines[i] = json.dumps(json.loads(line), ensure_ascii=False)
                except:
                    pass
        return '\n'.join(lines)

    def process_sct(self, outputs: list[str]) -> tuple[list[str | list[str | dict] | BaseMessage], int]:
        """
        修复生成的输出列表，解析每个输出并尝试修复无法解析的输出。

        参数:
            outputs (list[str]): 初步生成的输出列表。

        返回:
            list[str]: 修复后的输出列表。
            int: 总尝试修复次数
        """

        def try_fix_output(output: str) -> str:
            nonlocal remaining_fixes, total_attempt
            raw_action = output
            attempt = 0
            while attempt < self.fixing_num and remaining_fixes > 0:
                try:
                    # 尝试解析输出
                    parsed_result = self.tool_parser.parse(output)
                    # 尝试执行解析后得到的Action
                    observation = execute_action(tools=self.tools, action=parsed_result)
                    break  # 修复成功，跳出循环
                except Exception as e:
                    error_message = str(e)
                    attempt += 1
                    total_attempt += 1
                    remaining_fixes -= 1

                    # 如果解析失败，尝试修复
                    fixing_prompt = self._initialize_fixing_prompt(
                        prompt=self.fixing_prompt,
                        error=error_message,
                        raw_action=raw_action,
                        cur_action=output
                    )
                    fixing_prompt_str = fixing_prompt.format_prompt().text
                    # 使用 fixing_model 修复输出
                    output = chat_with_model_str(self.fixing_model, fixing_prompt_str, return_str=True)
            return output

        repaired_outputs = []
        total_attempt = 0
        remaining_fixes = self.fixing_num * len(outputs)  # 总修复次数

        # 第一遍：每个输出都有机会修复fixing_num次
        for output in outputs:
            repaired_outputs.append(try_fix_output(output))

        # 第二遍：如果启用动态修复并且还有剩余的修复次数，继续修复
        if self.dynamic_fixing and remaining_fixes > 0:
            for i, output in enumerate(repaired_outputs):
                if remaining_fixes <= 0:
                    break  # 没有剩余的修复次数了
                repaired_outputs[i] = try_fix_output(output)

        return repaired_outputs, total_attempt
