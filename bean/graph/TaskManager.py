import asyncio
from langchain_openai import ChatOpenAI

from bean.executor.graphExecutor import GraphExecutor
from bean.graph.Graph import Graph
from bean.memory.BaseMemory import BaseMemory
from bean.parser.StructuredConclusionOuputParser import StructuredConclusionOutputParser
from bean.resources.pod import Pod
from bean.stage.base.ActionStage import ActionStage
from bean.stage.base.BaseStage import BaseStage
from setting.prompt_Conclusion import MAIN_PROMPT
from setting.prompt_Extract import EXTRACT


class TaskManager:
    def __init__(self, pod: Pod, max_concurrent_executions: int):
        self.graphs = {}  # 存储图的字典，key 为图的 id，value 为 Graph 对象
        self.tree_relationships = {}  # 存储树结构关系
        self.executors = {}  # 用于存储每个图对应的 executor
        self.pod = pod
        self.max_concurrent_executions = max_concurrent_executions  # 最大并发数

        # 初始化提取阶段（ActionStage），用于从结果中提取结论
        self.extract_stage = ActionStage(
            prompt=EXTRACT,
            tools=[],
            tool_parser=StructuredConclusionOutputParser(),
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

        self.conclusion_stage = BaseStage(
            prompt=MAIN_PROMPT,
            chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16",
                                  base_url="http://localhost:11434/v1",
                                  api_key="<KEY>")
        )

        self.memory = BaseMemory(20, extract_stage=self.extract_stage, conclusion_stage=self.conclusion_stage)

    def add_graph(self, graph: Graph):
        self.graphs[graph.graph_id] = graph

    def add_tree_relationship(self, tree_data: list):
        for tree in tree_data:
            self.tree_relationships[tree['id']] = {
                "label": tree['label'],
                "children": [
                    {
                        "id": child['id'],
                        "name": child['name'],
                        "category": child['category'],
                        "purpose": child['purpose']
                    }
                    for child in tree.get('children', [])
                ]
            }

    def to_json(self) -> dict:
        return {
            "flowDataMap": [
                [graph_id, graph.to_json()] for graph_id, graph in self.graphs.items()
            ],
            "treeData": [
                {
                    "id": tree_id,
                    "label": tree['label'],
                    "children": tree['children']
                } for tree_id, tree in self.tree_relationships.items()
            ]
        }

    @staticmethod
    def from_data(json_data: dict, pod: Pod, max_concurrent_executions: int):
        task_manager = TaskManager(pod, max_concurrent_executions)

        # 构建一个字典以快速查找 treeData 中的图信息
        tree_info_map = {}
        for tree in json_data.get("treeData", []):
            for child in tree.get("children", []):
                tree_info_map[child['id']] = {
                    "name": child['name'],
                    "category": child['category'],
                    "purpose": child['purpose']
                }

        # 解析 flowDataMap，并根据 treeData 进行图的信息补充
        for flow_data_map in json_data.get("flowDataMap", []):
            graph_id = flow_data_map[0]
            flow_data = flow_data_map[1]

            # 从 tree_info_map 中获取与该图相关的 name, category, purpose
            graph_info = tree_info_map.get(graph_id, {})
            graph_name = graph_info.get("name", "")
            graph_category = graph_info.get("category", "")
            graph_purpose = graph_info.get("purpose", "")

            # 构建 Graph 对象
            graph = Graph.from_flow_data_map(graph_id, flow_data, graph_name, graph_category, graph_purpose)
            task_manager.add_graph(graph)

            # 为每个图构建 executor
            executor = GraphExecutor(
                memory=task_manager.memory,  # 使用 TaskManager 中的 memory 实例
                graph=graph,  # 当前的 Graph 实例
                pod=task_manager.pod,  # 替换为实际的 Pod 对象
                extract_stage=task_manager.extract_stage,  # 使用 TaskManager 中的 extract_stage
                conclusion_stage=task_manager.conclusion_stage  # 使用 TaskManager 中的 conclusion_stage
            )
            task_manager.executors[graph_id] = executor

        # 解析 treeData 并添加到 TaskManager
        tree_data = json_data.get("treeData", [])
        task_manager.add_tree_relationship(tree_data)

        return task_manager

    async def execute_all(self):
        """
        异步执行所有的 executors，并限制最大并发数。
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_executions)

        async def run_executor(executor):
            async with semaphore:
                await executor.execute()

        tasks = [run_executor(executor) for executor in self.executors.values()]
        await asyncio.gather(*tasks)
