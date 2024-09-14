import asyncio
from dataclasses import field, dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union, Callable, Set

from bean.graph.Graph import Graph
from utils.str_utils import process_regex
from utils.tools import execute_action


@dataclass
class QuestionNodePair:
    """
    QuestionNodePair 现在使用字典结构存储问题与节点ID的映射关系。
    question 为 key，node_ids 为 set 存储。
    """
    question_node_map: Dict[str, Set[str]] = field(default_factory=dict)

    def add_node_ids(self, question: str, node_ids: Optional[Union[str, Set[str]]]):
        """
        向 question_node_map 添加新的节点ID。
        如果 question 已存在，则将 node_ids 添加到对应的 set 中。
        如果 question 不存在，则创建一个新的条目。

        Args:
            question (str): 问题，作为 key。
            node_ids (Optional[Union[str, Set[str]]]): 可以是节点ID的字符串或 set。
        """
        # 如果 node_ids 是单个字符串，将其转换为 set
        if isinstance(node_ids, str):
            node_ids = {node_ids}
        elif node_ids is None:
            node_ids = set()

        # 如果 question 已经存在，更新 node_ids 集合
        if question in self.question_node_map:
            self.question_node_map[question].update(node_ids)
            print(f"已更新问题 '{question}'，添加的 node_ids: {node_ids}")
        else:
            # 否则创建新的 question -> node_ids 映射
            self.question_node_map[question] = node_ids
            print(f"新增问题 '{question}'，以及其对应的 node_ids: {node_ids}")

    def to_dict(self, current_graph_obj: Graph) -> dict:
        """
        将 QuestionNodePair 对象转换为字典格式，便于存储和序列化。
        对于每个 question，返回 question 作为 key，node_ids 和对应 conclusion 作为值。

        Args:
            current_graph_obj (Any): 用于获取节点对象并提取 conclusion 的图表对象。

        Returns:
            dict: 包含 question、node_ids 及其对应 conclusion 的字典。
        """
        question_conclusion_map = {}
        for question, node_ids in self.question_node_map.items():
            question_conclusions = {
                "question": question,
                "nodes": []
            }
            for node_id in node_ids:
                # 通过 current_graph_obj 获取每个 node_id 对应的节点，并获取其 conclusion
                node_obj = current_graph_obj.get_node(node_id)
                question_conclusions["nodes"].append({
                    "node_id": node_id,
                    "conclusion": node_obj.conclusion if node_obj else None
                })
            question_conclusion_map["conclusions"] = question_conclusions

        return question_conclusion_map

    @staticmethod
    def from_dict(data: dict) -> 'QuestionNodePair':
        """
        从字典中重建 QuestionNodePair 对象。

        Args:
            data (dict): 包含 question 与 node_ids 数据的字典。

        Returns:
            QuestionNodePair: 生成的 QuestionNodePair 对象。
        """
        question_node_map = {question: set(node_ids) for question, node_ids in data.items()}
        return QuestionNodePair(question_node_map=question_node_map)



class NodeMemoryItem:
    """
    NodeMemoryItem 类用于存储与某个动作（action）相关的观察、问题与节点ID的映射。
    """

    def __init__(self, action: str,
                 observation: str,
                 description: str,
                 question_node_pair: Optional[QuestionNodePair] = None,
                 timestamp: Optional[datetime] = None):
        """
        初始化 NodeMemoryItem 对象。

        Args:
            action (str): 需要存储的动作对象。
            observation (str): 观察到的内容。
            description (str): 该条记忆的描述。
            question_node_pair (QuestionNodePair, optional): 与问题和节点ID映射的对象。
            timestamp (datetime, optional): 上次执行时间。默认使用当前时间。
        """
        self.action = action
        self.observation = observation
        self.description = description
        self.question_node_pair = question_node_pair if question_node_pair else QuestionNodePair()
        self.timestamp = timestamp if timestamp else datetime.now()

    def add_question_node_pair(self, question: str, node_ids: Optional[Union[str, Set[str]]]):
        """
        向 NodeMemoryItem 中的 question_node_map 添加新的 question 和 node_ids。

        Args:
            question (str): 问题作为 key。
            node_ids (Optional[Union[str, Set[str]]]): 节点ID，可以是单个字符串或 set。
        """
        self.question_node_pair.add_node_ids(question, node_ids)

    async def run_action_and_update(self, get_graph_func: Callable, llm_extract_func: Callable):
        """
        异步执行动作，使用 asyncio.gather 并行更新所有 Question 的 Conclusion。
        如果正则表达式为空，则调用 LLM 提取关键信息。

        Args:
            llm_extract_func (callable, optional): 提供的 LLM 提取关键信息的异步函数。
            get_graph_func (callable): 获取最新图表信息的函数。
        """
        # 执行动作，获取结果
        result = execute_action(self.action)
        self.observation = result

        # 获取当前最新图表信息
        current_graph_obj = get_graph_func

        # 创建并发任务列表
        tasks = []

        # 遍历 question 和对应的 node_ids
        for question, node_ids in self.question_node_pair.question_node_map.items():
            # 对每个 question，处理其 node_ids
            tasks.append(
                self._process_question_node_ids(result, question, node_ids, current_graph_obj, llm_extract_func))

        # 并发执行所有任务
        await asyncio.gather(*tasks)

        # 更新最后执行时间
        self.timestamp = datetime.now()

    async def _process_question_node_ids(self, result: str, question: str, node_ids: Set[str], current_graph_obj: Any,
                                         llm_extract_func: Callable):
        """
        处理单个 Question 及其所有 Node IDs，获取结论并更新对应的 Node 对象。

        Args:
            result (str): 执行动作的结果。
            question (str): 问题字符串。
            node_ids (Set[str]): 与问题关联的节点ID集合。
            current_graph_obj (Any): 图表对象，用于获取节点。
            llm_extract_func (Callable): 提供的 LLM 提取关键信息的异步函数。
        """
        # 获取 node_ids 集合中的第一个节点来处理
        first_node_id = next(iter(node_ids))
        first_node_obj = current_graph_obj.get_node(first_node_id)

        # 处理正则或 LLM 提取
        if first_node_obj.regex:
            # 使用正则表达式进行匹配
            conclusion = await process_regex(result, first_node_obj.regex)
        else:
            # 如果没有正则表达式，调用 LLM 提取关键信息
            if llm_extract_func:
                conclusion = await llm_extract_func(result, question)
            else:
                conclusion = await self.handle_no_llm_func(question)

        # 将结论应用到所有相同问题的节点
        for node_id in node_ids:
            node_obj = current_graph_obj.get_node(node_id)
            node_obj.conclusion = conclusion

    def to_dict(self, get_graph_func: Callable) -> Dict[str, Any]:
        """
        将 NodeMemoryItem 对象转换为字典格式，便于存储和序列化。

        Returns:
            Dict[str, Any]: 包含动作、观察、描述、问题和时间戳的字典。
        """
        graph_obj = get_graph_func
        return {
            "action": self.action,
            "observation": self.observation,
            "description": self.description,
            "question_node_pairs": self.question_node_pair.to_dict(graph_obj),
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
            observation=item_dict["observation"],
            description=item_dict["description"],
            question_node_pair=question_node_pair,
            timestamp=timestamp
        )


    async def handle_no_llm_func(self, question: str) -> str:
        """
        处理没有提供 LLM 提取函数的情况，返回提示信息。

        Args:
            question (str): 未提供 LLM 提取函数时的问题。

        Returns:
            str: 处理后的提示信息。
        """
        return f"LLM 提取所需的函数未提供，问题: {question}"


class MemoryItemFactory:
    """
    MemoryItemFactory 是一个工厂类，用于根据给定的参数构造 NodeMemoryItem 对象。
    """

    @staticmethod
    def create_memory_item(action: str, observation: str, description: str, question: str,
                           node_ids: Union[str, Set[str]]) -> 'NodeMemoryItem':
        """
        根据传入的参数创建 NodeMemoryItem 对象。

        Args:
            action (str): 动作名称。
            observation (str): 观察内容。
            description (str): 描述信息。
            question (str): 相关的问题。
            node_ids (Union[str, Set[str]]): 与问题关联的节点ID，可以是单个字符串或集合。

        Returns:
            NodeMemoryItem: 创建并返回 NodeMemoryItem 对象。
        """
        # 创建 QuestionNodePair 对象并添加节点ID
        question_node_pair = QuestionNodePair()
        question_node_pair.add_node_ids(question, node_ids)

        # 创建 NodeMemoryItem 对象并添加 question_node_pair
        memory_item = NodeMemoryItem(
            action=action,
            observation=observation,
            description=description,
            question_node_pair=question_node_pair,
            timestamp=datetime.now()

        )

        return memory_item

    @staticmethod
    def create_error_memory_item(description: str, node_ids: Union[str, Set[str]]) -> 'NodeMemoryItem':
        # 创建 QuestionNodePair 对象并添加节点ID
        question_node_pair = QuestionNodePair()
        question_node_pair.add_node_ids(description, node_ids)

        # 创建 NodeMemoryItem 对象并添加 question_node_pair
        memory_item = NodeMemoryItem(
            action="error",
            observation="error",
            description=description,
            question_node_pair=question_node_pair,
            timestamp=datetime.now()

        )

        return memory_item
