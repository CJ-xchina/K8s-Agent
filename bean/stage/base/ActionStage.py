import asyncio
import json
from collections import Counter
from typing import List, Callable, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from bean.parser.BaseOutputParser import BaseOutputParser
from bean.stage.base.BaseStage import BaseStage
from setting.prompt_Action import NAIVE_FIX, MAIN_PROMPT, CONCLUSION
from utils.chat import chat_with_model_str
from utils.tools import extract_tool_signature, validate_tool_input


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
    def default_conclusion_prompt() -> str:
        return CONCLUSION

    @staticmethod
    def default_prompt() -> str:
        return MAIN_PROMPT

    @staticmethod
    def default_model() -> BaseChatModel:
        return ChatOpenAI(model="qwen2:7b-instruct-fp16", base_url="http://localhost:11434/v1",
                          api_key="<KEY>")

    def __init__(self,
                 prompt: str,

                 tools: List[BaseTool],
                 tool_parser: BaseOutputParser,
                 chat_model: BaseChatModel = None,
                 fixing_model: BaseChatModel = None,
                 self_consistency_times: int = 1,
                 enable_fixing: bool = False,
                 enable_conclusion: bool = False,
                 node_details_func: Callable = None,
                 fixing_prompt: str = None,
                 fixing_num: int = 3,
                 dynamic_fixing: bool = True):
        """
        初始化 ActionStage 类。

        Args:
            prompt (str): 用于对话的初始提示字符串。
            chat_model (BaseChatModel): 用于生成对话的语言模型实例。
            tools (List[BaseTool]): 可用工具的列表。
            tool_parser (BaseOutputParser): 用于解析工具操作输出的解析器。
            self_consistency_times (int): 自一致性次数。
            enable_fixing (bool): 是否启用修复功能。
            fixing_model (BaseChatModel): 用于修复输出的模型。
            fixing_prompt (str): 用于修复输出的模型的提示词。
            fixing_num (int): 修复次数。
            dynamic_fixing (bool): 是否启用动态修复。
            enable_conclusion (bool): 是否启用结论阶段。
        """
        self.enable_fixing = enable_fixing
        self.enable_conclusion = enable_conclusion
        self.tools = tools
        self.tool_parser = tool_parser
        self.chat_model = chat_model if chat_model is not None else self.default_model()
        self.get_node_details = node_details_func
        if enable_fixing:
            self.fixing_model = fixing_model if fixing_model is not None else chat_model
            self.fixing_prompt = fixing_prompt if fixing_prompt is not None else self.default_fixing_prompt()
            self.fixing_num = fixing_num
            self.dynamic_fixing = dynamic_fixing

        # 调用父类的初始化函数
        super().__init__(prompt,
                         chat_model,
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

        # 初始化参数字典
        partial_kwargs = {
            "tools": self.tool_parser.render_text_description_and_args(self.tools),  # 渲染工具描述
            "format_instructions": self.__chinese_friendly(self.tool_parser.get_format_instructions()),  # 处理格式说明
        }

        # 如果 prompt 中包含 'node_details'，则添加 'node_details' 参数
        if "node_details" in prompt:
            partial_kwargs["node_details"] = self.get_node_details()

        return PromptTemplate.from_template(prompt, template_format="jinja2").partial(**partial_kwargs)

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

        return PromptTemplate.from_template(prompt, template_format="jinja2").partial(
            tools=self.tool_parser.render_text_description_and_args(self.tools),  # 渲染工具描述
            format_instructions=self.__chinese_friendly(  # 处理格式说明
                self.tool_parser.get_format_instructions(),
            ),
            error=error,
            raw_action=raw_action,
            cur_action=cur_action,
        )

    def _initialize_conclusion_prompt(self, _prompt: str, observation: str, _question: str) -> PromptTemplate:
        """
        将字符串类型的提示转换为 PromptTemplate 对象，用于生成结论。

        参数:
            observation (str): 需要分析的数据或观察结果的原始字符串。
            _prompt (str): 原始字符串类型的提示，用于引导生成结论。
            _question (str): 针对数据提出的需要回答的问题。

        返回:
            PromptTemplate: 转换后的模板对象。

        抛出:
            ValueError: 如果传入的 observation、_prompt 或 _question 为空或不是字符串类型。
        """

        return PromptTemplate.from_template(_prompt, template_format="jinja2").partial(
            raw_input=observation,
            question=_question
        )

    def select_final_output(self, outputs: list[str]) -> str:
        """
        选择最终输出的方法，基于工具名称和参数的一致性来判断哪个输出最常见，
        并返回符合该签名的输出中长度处于中间位置的输出。

        Args:
            outputs (list[str]): 所有生成的输出列表。

        Returns:
            str: 选择的最终输出。

        Raises:
            ValueError: 如果输出列表为空。
        """
        if not outputs:
            raise ValueError("输出列表不能为空")

        # 用于存储成功解析的签名和对应的输出
        valid_signatures = []
        valid_outputs = []

        for output in outputs:
            try:
                # 尝试解析输出，提取工具名称和参数签名
                signature = extract_tool_signature(output, self.tool_parser)
                valid_signatures.append(signature)
                valid_outputs.append(output)
            except Exception as e:
                continue

        if not valid_signatures:
            raise RuntimeError("所有的输出解析均失败，未能找到匹配的输出。")

        # 找到出现次数最多的签名
        most_common_signature, _ = Counter(valid_signatures).most_common(1)[0]

        # 获取所有匹配的输出及其长度
        matched_outputs = [output for output, signature in zip(valid_outputs, valid_signatures) if
                           signature == most_common_signature]

        if not matched_outputs:
            raise RuntimeError("未能找到匹配的输出。")

        # 按长度排序
        matched_outputs.sort(key=len)

        # 获取中间位置的输出
        middle_index = len(matched_outputs) // 2
        selected_output = matched_outputs[middle_index]
        return selected_output

    def _step(self, variables=None):
        """
        调用父类的 _step 方法生成对话输出，并根据输出执行相应的工具操作，返回生成的响应。

        Args:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        """
        # 调用父类的 _step 方法获取初步输出
        final_output = super()._step(variables)

        # 解析生成的响应以确定是否需要调用工具
        action = self.tool_parser.parse(final_output)

        return action

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

    async def process_sct(self, outputs: list[str]) -> tuple[list[str], int] | tuple[tuple[Any], int]:
        """
        修复生成的输出列表，解析每个输出并尝试修复无法解析的输出。

        参数:
            outputs (list[str]): 初步生成的输出列表。

        返回:
            list[str]: 修复后的输出列表。
            int: 总尝试修复次数
        """

        async def try_fix_output(output: str) -> str:
            nonlocal remaining_fixes, total_attempt
            raw_action = output
            attempt = 0
            while attempt < self.fixing_num and remaining_fixes > 0:
                try:
                    # 尝试解析输出
                    parsed_result = self.tool_parser.parse(output)
                    # 尝试执行解析后得到的Action
                    validate_tool_input(tools=self.tools, action=parsed_result)
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
                    output = await chat_with_model_str(self.fixing_model, fixing_prompt_str, return_str=True)
            return output

        if not self.enable_fixing:
            return outputs, 0

        repaired_outputs = []
        total_attempt = 0
        remaining_fixes = self.fixing_num * len(outputs)  # 总修复次数

        # 第一遍：每个输出都有机会修复fixing_num次
        tasks = [try_fix_output(output) for output in outputs]
        repaired_outputs = await asyncio.gather(*tasks)


        # 第二遍：如果启用动态修复并且还有剩余的修复次数，继续修复
        if self.dynamic_fixing and remaining_fixes > 0:
            tasks = [try_fix_output(output) for output in repaired_outputs if remaining_fixes > 0]
            repaired_outputs = await asyncio.gather(*tasks)

        return repaired_outputs, total_attempt
