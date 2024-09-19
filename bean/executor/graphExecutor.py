import asyncio
from typing import List, Dict, Any

from bean.graph.Graph import Graph
from bean.graph.Node import Node
from bean.memory.BaseMemory import BaseMemory
from bean.memory.NodeMemoryItem import MemoryItemFactory, QuestionNodePair
from bean.resources.pod import Pod
from bean.stage.base.BaseStage import BaseStage
from bean.workflow.baseWorkFlow import Workflow
from bean.workflow.workflowManager import WorkflowManager
from utils.StageUtils import StageUtils


class GraphExecutor:
    def __init__(self, memory: BaseMemory, graph: Graph, pod: Pod, extract_stage: BaseStage, conclusion_stage: BaseStage):
        """
        初始化 GraphExecutor 对象，创建 Graph 和 Memory 的实例，并初始化各个阶段的处理逻辑。

        参数:
            memory (BaseMemory): 内存对象，存储和管理执行过程中生成的 MemoryItem。
            graph (Graph): 图对象，包含节点和边的逻辑结构。
            pod (Pod): Pod 对象，包含特定资源和配置信息。
            extract_stage (BaseStage): 提取阶段对象，处理节点的提取逻辑。
            conclusion_stage (BaseStage): 结论阶段对象，处理节点的结论生成逻辑。
        """
        self.graph = graph  # 初始化图结构
        self.memory = memory  # 内存对象，用于存储执行过程中的数据
        self.pod = pod  # Pod 对象，包含特定资源和配置信息
        self.extract_stage = extract_stage  # 提取阶段对象
        self.conclusion_stage = conclusion_stage  # 结论阶段对象
        self.workflow_manager = WorkflowManager()  # 工作流管理器，管理所有的工作流

    async def execute(self):
        """
        执行 GraphExecutor 的主要逻辑，通过图中的节点进行决策和提取，存储数据到内存中。
        """
        # 创建初始工作流，从图的起始节点开始
        initial_node_id = self.graph.start_node_id
        initial_workflow = self.workflow_manager.create_workflow(initial_node_id)

        # 创建并启动初始任务
        initial_task = asyncio.create_task(self.process_workflow(initial_workflow))
        self.workflow_manager.add_task(initial_workflow.workflow_id, initial_task)

        # 持续监测并执行所有的工作流任务
        await self.workflow_manager.run_all_tasks()

    async def process_workflow(self, workflow: Workflow):
        """
        处理单个工作流的执行逻辑。

        参数:
            workflow (Workflow): 要处理的工作流对象。
        """
        while True:
            try:
                # 获取当前工作流的节点
                current_node = self.graph.get_node(workflow.current_node_id)
                if not current_node:
                    # 无效的节点 ID，记录错误并结束工作流
                    print(f"工作流 {workflow.workflow_id} 遇到无效的节点 ID {workflow.current_node_id}，结束工作流。")
                    self.workflow_manager.remove_workflow(workflow.workflow_id)
                    break

                # 将当前节点加入到工作流的历史记录中
                workflow.add_to_history(current_node.node_id)

                # 处理不同类型的节点
                if current_node.node_type == "input":
                    # 如果是 input 节点，跳转到下一个节点
                    next_node_id = self.graph.jump_to_node_by_condition(workflow.current_node_id)
                    if next_node_id:
                        workflow.set_current_node(next_node_id)
                    else:
                        # 无下一个节点，结束工作流
                        self.workflow_manager.remove_workflow(workflow.workflow_id)
                        break

                elif current_node.node_type == "default":
                    # 分裂工作流，调用外部函数创建新的工作流
                    new_workflows = self.split_workflows_before_action(current_node, workflow)
                    for new_workflow in new_workflows:
                        # 为每个新工作流创建并启动任务
                        new_task = asyncio.create_task(self.process_workflow(new_workflow))
                        self.workflow_manager.add_task(new_workflow.workflow_id, new_task)

                    # 创建节点与大模型的交互配对对象
                    pair = QuestionNodePair()
                    pair.add_nodes(current_node.question, current_node)

                    # 执行提取操作，并更新节点的结论
                    await StageUtils.run_action_and_set_conclusion(pair, self.extract_stage)

                    # 创建 MemoryItem 并存储
                    item = MemoryItemFactory.create_memory_item(
                        action=current_node.action,
                        question=current_node.question,
                        pod=self.pod,
                        nodes=current_node
                    )

                    # 存储到内存，假设 store_data 是线程安全的
                    self.memory.store_data(item)

                    # 跳转到下一个节点
                    next_node_id = self.graph.jump_to_node_by_condition(workflow.current_node_id, current_node.conclusion)
                    if next_node_id:
                        workflow.set_current_node(next_node_id)
                    else:
                        self.workflow_manager.remove_workflow(workflow.workflow_id)
                        break

                elif current_node.node_type == "output":
                    # 处理 output 节点，创建错误 MemoryItem
                    item = MemoryItemFactory.create_error_memory_item(
                        description=current_node.description,
                        pod=self.pod,
                        nodes=current_node
                    )
                    self.memory.store_data(item)

                    # 输出节点一般为终止节点，不应继续执行跳转
                    print(f"工作流 {workflow.workflow_id} 到达输出节点 {current_node.node_id}，结束工作流。")
                    self.workflow_manager.remove_workflow(workflow.workflow_id)
                    break

                elif current_node.node_type == "group":
                    # 获取当前组的所有节点
                    group_nodes = [
                        node for node in self.graph.nodes.values()
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

                    input_map = {
                        "question": current_node.question,
                        "description": current_node.description,
                        "details": self.pod.get_info(),
                        "history": execute_prompt_str,
                        "conclusion": error_prompt_str
                    }

                    # 执行结论阶段
                    conclusion = self.conclusion_stage.step(input_map)
                    current_node.conclusion = conclusion

                    # 跳转到下一个节点（禁止更新工作流上下文）
                    next_node_id = self.graph.jump_to_node_by_condition(workflow.current_node_id, conclusion)
                    if next_node_id:
                        workflow.set_current_node(next_node_id)
                    else:
                        self.workflow_manager.remove_workflow(workflow.workflow_id)
                        break
            except Exception as e:
                # 捕获异常并打印日志，移除当前工作流
                print(f"工作流 {workflow.workflow_id} 处理时遇到错误：{e}")
                self.workflow_manager.remove_workflow(workflow.workflow_id)
                break

    def split_workflows_before_action(self, current_node: Node, workflow: Workflow) -> List[Workflow]:
        """
        调用外部函数，在执行主要动作之前分裂新的工作流。

        参数:
            current_node (Node): 当前节点对象。
            workflow (Workflow): 当前工作流对象。

        返回:
            List[Workflow]: 新创建的工作流列表。
        """
        possible_branches = self.graph.get_reachable_nodes(current_node.node_id)
        new_workflows = []

        for branch in possible_branches:
            # 创建新的上下文并生成新的工作流
            new_context = workflow.context.copy()
            new_context['branch'] = branch
            new_workflow = self.workflow_manager.create_workflow(current_node.node_id, new_context)
            new_workflows.append(new_workflow)

        return new_workflows
