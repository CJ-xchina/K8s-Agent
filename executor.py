from datetime import datetime

from langchain_openai import ChatOpenAI

from bean.graph.Graph import Graph
from bean.graph.Node import NodeStatusEnum
from bean.memory.MemoryItem import MemoryItemFactory
from bean.memory.baseMemory import baseMemory
from bean.parser.StructuredChatOutputParser import StructuredChatOutputParser
from bean.parser.StructuredConclusionOuputParser import StructuredConclusionOutputParser
from bean.resources.pod import Pod
from bean.stage.base.ActionStage import ActionStage
from setting.prompt_Action import NAIVE_FIX
from setting.prompt_Extract import EXTRACT
from setting.prompt_Thinking import THINKING_PROMPT
from tools.k8s_tools import kubectl_command
from utils.str_utils import process_regex
from utils.tools import execute_action


class PodAgent:
    def __init__(self, json_str: str = "", pod: Pod = None):
        """
        初始化 PodAgent 对象，创建 Graph 和 Memory 的实例，并初始化各个阶段的处理逻辑。

        参数:
            path (str): 图的文件路径。
            pod (Pod): 传入的Pod对象。
        """
        self.graph = Graph(json_str)  # 初始化图结构，传入路径
        self.memory = baseMemory(60, self.graph.get_graph_obj())  # 创建一个 baseMemory 实例，用于存储和管理 MemoryItem
        self.pod = pod  # 传入的Pod对象

        # 初始化思考阶段（ActionStage），用于决定下一步行动
        self.thinking_stage = ActionStage(
            prompt=THINKING_PROMPT,
            tools=[kubectl_command],
            tool_parser=StructuredChatOutputParser(),
            chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16",
                                  base_url="http://localhost:11434/v1",
                                  api_key="<KEY>"),  # OpenAI 的 Chat 模型
            enable_fixing=True,
            fixing_model=ChatOpenAI(model="qwen2:7b-instruct-fp16",
                                    base_url="http://localhost:11434/v1",
                                    api_key="<KEY>"),  # 修复模型
            fixing_prompt=NAIVE_FIX,
            self_consistency_times=7,  # 多次自我一致性检查
            execute_action=False  # 不直接执行 action
        )

        # 初始化提取阶段（ActionStage），用于从结果中提取结论
        self.extract_stage = ActionStage(
            prompt=EXTRACT,
            tools=[],
            tool_parser=StructuredConclusionOutputParser(
                self.graph.get_current_node_if_statement
            ),
            chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16",
                                  base_url="http://localhost:11434/v1",
                                  api_key="<KEY>"),  # 使用同样的模型进行提取
            enable_fixing=False,
            fixing_model=ChatOpenAI(model="qwen2:7b-instruct-fp16",
                                    base_url="http://localhost:11434/v1",
                                    api_key="<KEY>"),
            self_consistency_times=11,
            execute_action=False  # 不直接执行 action
        )

    def execute(self):
        current_node = self.graph.get_current_node()  # 获取当前节点

        """
        执行PodAgent的主要逻辑，通过图中的节点进行决策和提取，存储数据到内存中。
        """
        while not self.graph.is_current_node_terminal():  # 当当前节点不是终止节点时，继续执行
            question = current_node.question

            current_node.status = NodeStatusEnum.EXECUTING
            current_node.start_time = datetime.now()

            if current_node.action == "":
                # 如果当前节点没有指定 action，则通过思考阶段进行决策
                # 获取历史决策信息填入history中
                history = self.memory.get_all_summaries()

                # 获取当前问题

                input_map = {
                    "history": history,
                    "question": question,
                    "details": self.pod.get_info()
                }
                current_node.action, observation = self.thinking_stage.step(input_map)

            # 执行指定的 action，并获取观察结果
            observation = execute_action(current_node.action, pod=self.pod)

            # 如果当前节点存在正则表达式，使用正则表达式处理观察结果
            if current_node.regex is not None and current_node.regex is not "":
                conclusion = process_regex(observation, current_node.regex)
            else:
                input_map = {
                    "raw_input": observation,
                    "question": question,
                    "details": self.pod.get_info()
                }
                # 否则，通过提取阶段获取数据
                action, conclusion = self.extract_stage.step(input_map)

            # 将提取的结论保存到当前节点
            current_node.conclusion = conclusion

            self.graph.jump_to_node_by_condition(action.tool)

            # 创建 MemoryItem 并存储
            item = MemoryItemFactory.create_memory_item(
                action=current_node.action,
                observation=observation,
                description=current_node.description,
                question=current_node.question,
                node_ids=current_node.node_id
            )

            # 将 MemoryItem 存储到 memory 中
            self.memory.store_data(item)
            current_node.start_time = datetime.now()

            # 更新当前节点
            current_node = self.graph.get_current_node()  # 获取当前节点

        final_reason = current_node.action

        json_map = self.memory.get_data()

        print("ok")
