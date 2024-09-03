import unittest
from unittest.mock import MagicMock, patch

from langchain.memory import ConversationSummaryMemory, ConversationBufferMemory
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from bean.graph.llmChatGraph import LlmChatGraph
from bean.stage.ActionStage import ActionStage
from client.output_parser import StructuredChatOutputParser
from setting.prompt_Action import GRAPH_PROMPT
from tools.graphTool import GraphTool


class TestActionStage(unittest.TestCase):

    def setUp(self):
        # 假设已经从某个 JSON 文件或字符串加载了 LlmChatGraph 实例
        graph = LlmChatGraph(json_source="../resources/pod_graph.json", start_node_id="1")

        # 初始化 GraphTool
        tool = GraphTool(graph=graph)
        # 定义工具和工具解析器
        tools = [tool]

        prompt = GRAPH_PROMPT
        tool_parser = StructuredChatOutputParser()
        # 创建 ActionStage 实例
        self.stage = ActionStage(
            prompt=prompt,
            tool_parser=tool_parser,
            tools=tools, self_consistency_times=30,
            Enable_fixing=True,
            fixing_num=3,
            memory=ConversationBufferMemory()
        )

    def test_step(self):
        Thought = {
            "user_input": "我们在Kubernetes集群中运行了一个Web应用，最近我们发现某个Pod频繁重启。在执行 `kubectl logs` 时，我们看到以下日志条目：'Error: ImagePullBackOff'。另外，`kubectl describe pod` 显示该Pod的 `Events` 部分记录了多次 'Failed to pull image' 事件。是否可以判断是用户的配置yaml问题？",
        }

        log = self.stage._step(Thought)
        print("--------------------------")
        print(log)

    def test_initialize_prompt(self):
        # 测试 _initialize_prompt 方法
        prompt_template = self.stage._initialize_prompt(self.prompt)
        self.assertIsInstance(prompt_template, PromptTemplate)
        self.assertEqual(prompt_template.template, self.prompt)

    def test_self_consistency_times_validation(self):
        # 测试 self_consistency_times 必须大于 0
        with self.assertRaises(ValueError):
            ActionStage(prompt=self.prompt, chat_model=self.chat_model, tools=self.tools, tool_parser=self.tool_parser,
                        self_consistency_times=0)

    def test_tool_execution_multiply(self):
        # 模拟模型输出并测试 Multiply 工具
        mock_output = '{"action": "multiply", "action_input": {"num1": 3, "num2": 4}}'
        self.tool_parser.parse = MagicMock(return_value=AgentAction("multiply", {"num1": 3, "num2": 4}))

        response = self.stage._step()
        self.assertEqual(response, "12")  # 确保工具执行正确

    def test_final_answer(self):
        # 模拟模型输出为 AgentFinish 动作
        mock_output = '{"action": "Final Answer", "action_input": "This is the final output."}'
        self.tool_parser.parse = MagicMock(
            return_value=AgentFinish({"output": "This is the final output."}, mock_output))

        response = self.stage._step()
        self.assertEqual(response, "This is the final output.")  # 确保最终输出正确

    def test_select_final_output(self):
        # 测试 select_final_output 类方法
        outputs = ["response1", "response1", "response2"]
        selected_output = self.stage.select_final_output(outputs)
        self.assertEqual(selected_output, "response1")

    def test_select_final_output_empty(self):
        # 测试 select_final_output 类方法对空列表的处理
        with self.assertRaises(ValueError):
            self.stage.select_final_output([])

    def test_action_fix_case_1(self):
        output1 = """
        ```
        {"action": "Multiply", "action_input": {"num1": "3", "num2": "4"}}
        ```
        """
        output2 = """
        `````
        {"tool": "multiply", "action_input": {"number1": 7, "number2": 8}}
        `````
        """
        output3 = """
        ```
        {"tool": "multiply", "tool_input": {"number_one": 7, "number_two": 8}}
        ```
        """

        outputs = [output1, output2, output3]
        outputs = self.stage.process_sct(outputs)
        return outputs

    def test_action_fix_case_2(self):
        output1 = """
        ```····```
        {{{{{{{{"tool": "Mul", "tool_input": {"nu{{{{m1": "three", "num2": 5}}}}}{{{{{{{{{{{{{{{{
        ``````````
        """
        output2 = """
        ```··
        {"tool": "Multiply_and_get", "action_input": {"num1": this is might be four, "num_two": six}}
        ```
        """
        output3 = """
        ```··
        {**"call_function"**: "Multiply_and_get_the_right_answer", 

        "input": {}{

            "vars": {
                "number_1_int" : "this is four",
                "number_2_int" : "six",
                "number_3_int" : "sizx"
            }

        }
        }}}}}
                }```
        """

        outputs = [output1, output2, output3]
        outputs = self.stage.process_sct(outputs)
        return outputs

    def test_action_fix_case_3(self):
        output1 = """
        ```··
        {"tool": "Multiply", "tool_input": {"num1": [3, 4], "num2": 6}}
        ```
        """
        output2 = """
        ```
        {"tool": "multiply", "tool_input": {"num1": "this is might be seven", "num2": 8}}
        ```
        """
        output3 = """
        ```
        {"tool": "Multiply", "tool_input": {"num1": null, "num2": 9}}
        ```
        """

        outputs = [output1, output2, output3]
        outputs = self.stage.process_sct(outputs)
        return outputs

    def test_select_final_output_case_1(self):
        outputs, times = self.test_action_fix_case_1()
        selected_output = self.stage.select_final_output(outputs)
        print(selected_output)

    def test_select_final_output_case_2(self):
        outputs, times = self.test_action_fix_case_2()
        selected_output = self.stage.select_final_output(outputs)
        print(selected_output)

    def test_select_final_output_case_3(self):
        outputs, times = self.test_action_fix_case_3()
        selected_output = self.stage.select_final_output(outputs)
        print(selected_output)


if __name__ == '__main__':
    unittest.main()
