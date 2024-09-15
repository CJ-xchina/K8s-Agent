import asyncio
import logging
from dataclasses import field, dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union, Set

from bean.graph.Node import Node
from bean.resources.pod import Pod
from bean.stage.base.BaseStage import BaseStage
from utils.StageUtils import StageUtils
from utils.str_utils import process_regex
from utils.tools import execute_action


@dataclass
class QuestionNodePair:
    """
    QuestionNodePair 使用字典结构存储问题与节点的映射关系。
    question 为 key，nodes 为 set 存储 Node 对象。
    """
    question_node_map: Dict[str, Set[Node]] = field(default_factory=dict)

    def add_nodes(self, question: str, nodes: Optional[Union[Node, Set[Node]]]):
        """
        向 question_node_map 添加新的 Node 对象。
        如果 question 已存在，则将 nodes 添加到对应的 set 中。
        如果 question 不存在，则创建一个新的条目。

        Args:
            question (str): 问题，作为 key。
            nodes (Optional[Union[Node, Set[Node]]]): 可以是单个 Node 对象或 Node 对象的集合。
        """
        if isinstance(nodes, Node):
            nodes = {nodes}
        elif nodes is None:
            nodes = set()

        if question in self.question_node_map:
            self.question_node_map[question].update(nodes)
            logging.debug(f"已更新问题 '{question}'，添加的 nodes: {nodes}")
        else:
            self.question_node_map[question] = nodes
            logging.debug(f"新增问题 '{question}'，以及其对应的 nodes: {nodes}")

    def to_dict(self) -> dict:
        """
        将 QuestionNodePair 对象转换为字典格式，便于存储和序列化。
        返回 question 作为 key，nodes 和对应 conclusion 作为值。
        """
        question_conclusion_map = {}
        for question, nodes in self.question_node_map.items():
            question_conclusions = {
                "question": question,
                "nodes": []
            }
            for node in nodes:
                question_conclusions["nodes"].append({
                    "node_id": node.node_id,
                    "conclusion": node.conclusion if node else None
                })
            question_conclusion_map[question] = question_conclusions

        return question_conclusion_map

    @staticmethod
    def from_dict(data: dict) -> 'QuestionNodePair':
        """
        从字典中重建 QuestionNodePair 对象。

        Args:
            data (dict): 包含 question 与 node 数据的字典。

        Returns:
            QuestionNodePair: 生成的 QuestionNodePair 对象。
        """
        question_node_map = {}
        for question, node_data in data.items():
            nodes = {Node(**node_dict) for node_dict in node_data["nodes"]}
            question_node_map[question] = nodes
        return QuestionNodePair(question_node_map=question_node_map)


class NodeMemoryItem:
    """
    NodeMemoryItem 类用于存储与某个动作（action）相关的观察、问题与节点的映射。
    """

    def __init__(self, action: str,
                 pod: Pod,
                 question_node_pair: Optional[QuestionNodePair] = None,
                 timestamp: Optional[datetime] = None):
        """
        初始化 NodeMemoryItem 对象。

        Args:
            action (str): 需要存储的动作对象。
            pod (Pod): 与节点关联的 Pod 对象。
            question_node_pair (QuestionNodePair, optional): 与问题和节点映射的对象。
            timestamp (datetime, optional): 上次执行时间。默认使用当前时间。
        """
        self.pod = pod
        self.action = action
        self.question_node_pair = question_node_pair if question_node_pair else QuestionNodePair()
        self.timestamp = timestamp if timestamp else datetime.now()

    def add_question_node_pair(self, question: str, nodes: Optional[Union[Node, Set[Node]]]):
        """
        向 NodeMemoryItem 中的 question_node_map 添加新的 question 和 nodes。

        Args:
            question (str): 问题作为 key。
            nodes (Optional[Union[Node, Set[Node]]]): 节点对象，可以是单个 Node 或 set。
        """
        self.question_node_pair.add_nodes(question, nodes)

    async def run_action_and_update(self, extract_stage: BaseStage, max_concurrency: int = 5):
        """
        异步执行动作，提取结论并更新节点，使用 StageUtils 工具类来进行并发控制和提取处理。

        Args:
            extract_stage (BaseStage): 提取逻辑的执行阶段。
            max_concurrency (int): 最大并发任务数量。
        """
        try:
            # 使用 StageUtils 工具类执行动作并处理结论
            await StageUtils.run_action_and_set_conclusion(self.question_node_pair, extract_stage, max_concurrency, self.pod)
            self.timestamp = datetime.now()  # 更新执行时间戳
        except Exception as e:
            print(f"执行动作 '{self.action}' 时发生错误: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        将 NodeMemoryItem 对象转换为字典格式，便于存储和序列化。

        Returns:
            Dict[str, Any]: 包含动作、问题和时间戳的字典。
        """
        return {
            "action": self.action,
            "question_node_pairs": self.question_node_pair.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(item_dict: Dict[str, Any]) -> 'NodeMemoryItem':
        """
        从字典中重建 NodeMemoryItem 对象。

        Args:
            item_dict (Dict[str, Any]): 存储数据的字典。

        Returns:
            NodeMemoryItem: 生成的 NodeMemoryItem 对象。
        """
        timestamp = datetime.fromisoformat(item_dict["timestamp"])
        action = item_dict["action"]
        question_node_pair = QuestionNodePair.from_dict(item_dict["question_node_pairs"])

        return NodeMemoryItem(
            action=action,
            pod=None,  # 需要传入实际的 Pod 对象
            question_node_pair=question_node_pair,
            timestamp=timestamp
        )


from datetime import datetime
from typing import Union, Set

class MemoryItemFactory:
    """
    MemoryItemFactory 是一个工厂类，用于根据给定的参数构造 NodeMemoryItem 对象。
    """

    @staticmethod
    def create_memory_item(action: str, pod: Pod, question: str, nodes: Union[Node, Set[Node]]) -> 'NodeMemoryItem':
        """
        根据传入的参数创建 NodeMemoryItem 对象。

        Args:
            action (str): 动作名称。
            pod (Pod): 与该动作相关联的 Pod 对象。
            question (str): 相关的问题。
            nodes (Union[Node, Set[Node]]): 与问题关联的 Node 对象，可以是单个对象或集合。

        Returns:
            NodeMemoryItem: 创建并返回 NodeMemoryItem 对象。
        """
        # 确保 nodes 为 Set 类型
        if isinstance(nodes, Node):
            nodes = {nodes}
        elif not isinstance(nodes, set):
            raise TypeError("nodes 必须是 Node 类型的对象或 Node 的集合")

        # 创建 QuestionNodePair 对象并添加 Node 对象
        question_node_pair = QuestionNodePair()
        question_node_pair.add_nodes(question, nodes)

        # 创建并返回 NodeMemoryItem 对象
        memory_item = NodeMemoryItem(
            action=action,
            pod=pod,
            question_node_pair=question_node_pair,
            timestamp=datetime.now()
        )

        return memory_item

    @staticmethod
    def create_error_memory_item(description: str, pod: Pod, nodes: Union[Node, Set[Node]]) -> 'NodeMemoryItem':
        """
        创建一个表示错误的 NodeMemoryItem 对象。

        Args:
            description (str): 错误描述。
            pod (Pod): 与错误相关联的 Pod 对象。
            nodes (Union[Node, Set[Node]]): 关联的 Node 对象。

        Returns:
            NodeMemoryItem: 表示错误的 NodeMemoryItem 对象。
        """
        # 确保 nodes 为 Set 类型
        if isinstance(nodes, Node):
            nodes = {nodes}
        elif not isinstance(nodes, set):
            raise TypeError("nodes 必须是 Node 类型的对象或 Node 的集合")

        # 创建 QuestionNodePair 对象并添加 Node 对象
        question_node_pair = QuestionNodePair()
        question_node_pair.add_nodes(description, nodes)

        # 创建并返回 NodeMemoryItem 对象，动作设置为 "error"
        memory_item = NodeMemoryItem(
            action="error",
            pod=pod,
            question_node_pair=question_node_pair,
            timestamp=datetime.now()
        )

        return memory_item
