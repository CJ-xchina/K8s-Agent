from datetime import datetime

from langchain_openai import ChatOpenAI

from bean.graph.Graph import Graph
from bean.graph.Node import NodeStatusEnum
from bean.memory.NodeMemoryItem import MemoryItemFactory
from bean.memory.baseMemory import baseMemory
from bean.parser.StructuredConclusionOuputParser import StructuredConclusionOutputParser
from bean.resources.pod import Pod
from bean.stage.base.ActionStage import ActionStage
from setting.prompt_Extract import EXTRACT
from utils.str_utils import process_regex
from utils.tools import execute_action


class graphExecutor:
    def __init__(self, memory: baseMemory, graph: Graph, pod: Pod, ):
        """
        初始化 PodAgent 对象，创建 Graph 和 Memory 的实例，并初始化各个阶段的处理逻辑。

        参数:
            path (str): 图的文件路径。
            pod (Pod): 传入的Pod对象。
        """
        self.graph = graph  # 初始化图结构，传入路径
        self.memory = memory
        self.pod = pod  # 传入的Pod对象
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

        condition_value = None
        """
        执行PodAgent的主要逻辑，通过图中的节点进行决策和提取，存储数据到内存中。
        """
        while not self.graph.jump_to_node_by_condition(condition_value):  # 当当前节点不是终止节点时，继续执行

            current_node = self.graph.get_current_node()  # 获取当前节点

            if current_node.node_type == "input":
                # 如果是 input 节点，直接跳转到下一个节点
                condition_value = None
                continue

            elif current_node.node_type == "default":
                # 处理 default 节点
                question = current_node.question

                current_node.status = NodeStatusEnum.EXECUTING
                current_node.start_time = datetime.now()

                # 执行指定的 action，并获取观察结果
                observation = execute_action(current_node.action, pod=self.pod)

                # 如果当前节点存在正则表达式，使用正则表达式处理观察结果
                if current_node.regex is not None and current_node.regex != "":
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

                # 跳转到下一个节点
                condition_value = action.tool

                # 创建 MemoryItem 并存储
                item = MemoryItemFactory.create_memory_item(
                    action=current_node.action,
                    observation=observation,
                    description=current_node.description,  # 如果没有描述，自己写
                    question=current_node.question,
                    node_ids=current_node.node_id
                )
                # 将 MemoryItem 存储到 memory 中
                self.memory.store_data(item)

            elif current_node.node_type == "output":
                # 如果是 output 节点，直接创建错误 MemoryItem
                item = MemoryItemFactory.create_error_memory_item(
                    description=current_node.description,
                    node_ids=current_node.node_id
                )
                # 将 MemoryItem 存储到 memory 中
                self.memory.store_data(item)
                condition_value = None

            elif current_node.node_type == "group:":
                # 处理group的逻辑
                print("...")

        final_reason = current_node.action

        json_map = self.memory.get_data()

        print("ok")
