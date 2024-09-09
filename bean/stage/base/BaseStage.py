import asyncio

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from utils.chat import chat_with_model_template_batch


class BaseStage:
    """
    BaseStage 类用于实现基础对话逻辑。

    属性:
        prompt (PromptTemplate): 存储对话提示的模板。
        chat_model (BaseChatModel): 用于生成对话输出的语言模型。
        self_consistency_times (int): 用于生成多次对话输出以增强一致性。
    """

    def __init__(self, prompt: str, chat_model: BaseChatModel,
                 self_consistency_times: int = 1):
        """
        初始化 BaseStage 类。

        参数:
            prompt (str): 用于对话的初始提示字符串。
            chat_model (BaseChatModel): 用于生成对话的语言模型实例。
            self_consistency_times (int): 表示自一致性次数，必须大于0。

        抛出:
            ValueError: 如果 self_consistency_times 小于1则抛出异常。
        """
        if self_consistency_times < 1:
            raise ValueError("self_consistency_times 必须大于0")

        self.prompt = prompt
        self.prompt_template = self._initialize_prompt(prompt)
        self.prompt = self._initialize_prompt(prompt)
        self.chat_model = chat_model
        self.self_consistency_times = self_consistency_times

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
        return PromptTemplate.from_template(prompt, template_format="jinja2")

    def _check_input_variables(self, variables: dict):
        # 提取 PromptTemplate 中所需的参数名
        required_keys = set(self.prompt_template.input_variables)

        # 提取传入的 variables 中的参数名
        provided_keys = set(variables.keys())

        # 检查是否有缺少的参数
        missing_keys = required_keys - provided_keys
        if missing_keys:
            raise ValueError(f"缺少的必要参数: {missing_keys}")

        # 检查是否有多余的参数
        extra_keys = provided_keys - required_keys
        if extra_keys:
            raise ValueError(f"提供了多余的参数: {extra_keys}")

    async def _step_with_sct(self, variables=None) -> list[str]:
        """
        生成多个输出以提高一致性，并返回生成的响应列表。

        参数:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        返回:
            list[str]: 语言模型生成的对话响应列表。

        抛出:
            RuntimeError: 如果生成输出列表为空。
            ValueError: 如果传入的 variables 与 PromptTemplate 的预期参数不匹配。
        """

        if variables is None:
            variables = {}

        self._check_input_variables(variables)

        # 准备多次输入变量的列表，模拟多个请求
        variables_list = [variables] * self.self_consistency_times

        # 执行批量推理
        outputs = await chat_with_model_template_batch(self.chat_model, self.prompt_template, variables_list,
                                                       return_str=True)

        if not outputs:
            raise RuntimeError("生成的输出为空，这可能是由于 chat_model 的生成过程出现问题。")

        return outputs

    def step(self, variables=None) -> str:
        """
        生成最终的对话响应，并选择最常见的输出作为最终输出。

        参数:
            variables (dict): 用于注入到 PromptTemplate 中的参数字典。

        返回:
            str: 选择后的最终输出。
        """
        # 初始化变量字典
        if variables is None:
            variables = {}

        # 生成初步的 self_consistency 数组
        outputs = asyncio.run(self._step_with_sct(variables))

        # 输出数据进一步处理,目前不做处理,子类中可能会有Action修复的逻辑
        outputs, times = asyncio.run(self.process_sct(outputs))

        # 根据 self_consistency 输出投票选出最终输出
        final_output = self.select_final_output(outputs)

        return final_output

    def select_final_output(self, outputs: list[str]) -> str:
        """
        选择最终输出的方法，默认实现为选择最常见的输出。
        子类可以重写该方法以实现自定义逻辑。

        参数:
            outputs (list[str]): 所有生成的输出列表。

        返回:
            str: 选择的最终输出。

        抛出:
            ValueError: 如果输出列表为空。
        """
        if not outputs:
            raise ValueError(
                "self_consistency 执行结束后LLM 输出列表为空, 可能存在下面两种可能：1. 所有的Action均解析失败 2. LLM 输出存在问题")
        selected_output = max(set(outputs), key=outputs.count)
        return selected_output

    async def process_sct(self, outputs: list[str]) -> list[str]:
        """
        修复生成的输出列表，默认不对 outputs 进行任何修改。

        参数:
            outputs (list[str]): 初步生成的输出列表。

        返回:
            list[str]: 修复后的输出列表，默认返回原始列表。
        """
        # 默认不对 outputs 进行修改
        return outputs
