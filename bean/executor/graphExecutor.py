from bean.graph.Graph import Graph
from bean.memory.BaseMemory import BaseMemory
from bean.memory.NodeMemoryItem import MemoryItemFactory, QuestionNodePair
from bean.resources.pod import Pod
from bean.stage.base.BaseStage import BaseStage
from utils.StageUtils import StageUtils


class GraphExecutor:
    def __init__(self, memory: BaseMemory, graph: Graph, pod: Pod, extract_stage: BaseStage,
                 conclusion_stage: BaseStage):
        """
        初始化 PodAgent 对象，创建 Graph 和 Memory 的实例，并初始化各个阶段的处理逻辑。

        参数:
            path (str): 图的文件路径。
            pod (Pod): 传入的Pod对象。
        """
        self.graph = graph  # 初始化图结构，传入路径
        self.memory = memory
        self.pod = pod  # 传入的Pod对象
        # 设置与大模型的交互阶段
        self.extract_stage = extract_stage
        self.conclusion_stage = conclusion_stage

    async def execute(self):
        condition_value = None
        """
        执行 GraphExecutor 的主要逻辑，通过图中的节点进行决策和提取，存储数据到内存中。
        """
        while not self.graph.jump_to_node_by_condition(condition_value):  # 当当前节点不是终止节点时，继续执行

            current_node = self.graph.get_current_node()  # 获取当前节点

            # 添加当前节点 ID 到执行流
            self.graph.work_flow.append(current_node)

            if current_node.node_type == "input":
                # 如果是 input 节点，直接跳转到下一个节点
                condition_value = None
                continue

            elif current_node.node_type == "default":
                pair = QuestionNodePair()
                pair.add_nodes(current_node.question, current_node)

                # 更新节点conclusion
                await StageUtils.run_action_and_set_conclusion(pair, self.extract_stage)
                # 创建 MemoryItem 并存储
                item = MemoryItemFactory.create_memory_item(
                    action=current_node.action,
                    question=current_node.question,
                    pod=self.pod,
                    nodes=current_node
                )
                # 将 MemoryItem 存储到 memory 中
                self.memory.store_data(item)

            elif current_node.node_type == "output":
                # 如果是 output 节点，直接创建错误 MemoryItem
                item = MemoryItemFactory.create_error_memory_item(
                    description=current_node.description,
                    pod=self.pod,
                    nodes=current_node
                )
                # 将 MemoryItem 存储到 memory 中
                self.memory.store_data(item)
                condition_value = None

            elif current_node.node_type == "group":
                # 获取当前组的所有节点
                group_nodes = [
                    node for node in self.graph.nodes
                    if node.parent_node == current_node.node_id
                ]

                execute_prompt_str = ""
                error_prompt_str = ""

                # 按照顺序处理所有的 default 和 output 节点
                for node in group_nodes:
                    if node.node_type == "default":
                        execute_prompt_str += node.get_execution_summary()

                    if node.node_type == "output":
                        error_prompt_str += node.get_error_summary()
                        condition_value = False

                input_map = {
                    "question": current_node.question,
                    "description": current_node.description,
                    "details": self.pod.get_info(),
                    "history": execute_prompt_str,
                    "conclusion": error_prompt_str
                }
                conclusion = self.conclusion_stage.step(input_map)
                current_node.conclusion = conclusion
