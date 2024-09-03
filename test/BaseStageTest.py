import unittest
from unittest.mock import MagicMock
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from stage.stageType import StageType
from stage.BaseStage import BaseStage


class TestBaseStage(unittest.TestCase):

    def setUp(self):
        # 设置一个模拟的 BaseChatModel
        self.chat_model = ChatOpenAI(model="qwen2:7b", base_url="http://localhost:11434/v1", api_key="<KEY>")

        # 定义一个简单的提示
        self.prompt = "This is a test prompt."
        self.stage = BaseStage(prompt=self.prompt, chat_model=self.chat_model, self_consistency_times=3)

    def test_initialize_prompt(self):
        # 测试 _initialize_prompt 方法
        prompt_template = self.stage._initialize_prompt(self.prompt)
        self.assertIsInstance(prompt_template, PromptTemplate)
        self.assertEqual(prompt_template.template, self.prompt)

    def test_self_consistency_times_validation(self):
        # 测试 self_consistency_times 必须大于0
        with self.assertRaises(ValueError):
            BaseStage(prompt=self.prompt, chat_model=self.chat_model, self_consistency_times=0)

    def test_chat_with_model(self):
        # 测试 chat_with_model 方法
        variables = {"key": "value"}
        response = self.stage.chat_with_model(self.chat_model, self.stage.prompt, variables)
        self.assertGreater(len(response), 0)  # 确保生成了非空响应

    def test_step(self):
        # 测试 _step 方法生成多次输出并选择最终输出
        variables = {"key": "value"}
        final_output = self.stage._step(variables)
        self.assertIsInstance(final_output, str)  # 确保最终输出是字符串
        self.assertGreater(len(final_output), 0)  # 确保最终输出非空

    def test_step_with_missing_variables(self):
        # 测试 _step 方法在缺少必需变量时的处理
        self.stage.prompt.input_variables = ['required_key']
        with self.assertRaises(ValueError):
            self.stage._step(variables={})  # 不提供必要的变量

    def test_step_with_extra_variables(self):
        # 测试 _step 方法在提供多余变量时的处理
        self.stage.prompt.input_variables = ['required_key']
        variables = {'required_key': 'value', 'extra_key': 'extra_value'}
        with self.assertRaises(ValueError):
            self.stage._step(variables=variables)  # 提供了多余的变量

    def test_select_final_output(self):
        # 测试 select_final_output 类方法
        outputs = ["response1", "response1", "response2"]
        selected_output = self.stage.select_final_output(outputs)
        self.assertEqual(selected_output, "response1")

    def test_select_final_output_empty(self):
        # 测试 select_final_output 类方法对空列表的处理
        with self.assertRaises(ValueError):
            self.stage.select_final_output([])

    def test_select_final_output_all_unique(self):
        # 测试 select_final_output 当所有输出唯一时的行为
        outputs = ["response1", "response2", "response3"]
        selected_output = self.stage.select_final_output(outputs)
        self.assertIn(selected_output, outputs)  # 确保选择的输出在列表中

    def test_prompt_template_variables_validation(self):
        # 测试 _initialize_prompt 方法与 _step 方法中变量验证逻辑的综合
        self.stage.prompt.input_variables = ['key1', 'key2']
        variables = {'key1': 'value1', 'key2': 'value2'}
        formatted_prompt = self.stage.prompt.format_prompt(**variables)
        self.assertEqual(formatted_prompt, "This is a test prompt.")  # 假设 prompt 没有变化

    def test_incorrect_prompt_template(self):
        # 测试传入错误格式的 PromptTemplate 的处理
        with self.assertRaises(ValueError):
            self.stage._initialize_prompt("")

    def test_chat_with_model_empty_response(self):
        # 测试 chat_with_model 方法对空响应的处理
        variables = {"key": "value"}
        with self.assertRaises(ValueError):
            self.stage.chat_with_model(self.chat_model, self.stage.prompt, variables)


if __name__ == '__main__':
    unittest.main()
