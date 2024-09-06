import asyncio
import re
from dataclasses import field, dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union, Callable, Set

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

    def to_dict(self) -> dict:
        """
        将 QuestionNodePair 对象转换为字典格式，便于存储和序列化。

        Returns:
            dict: 包含 question 与 node_ids 映射的字典。
        """
        return {question: list(node_ids) for question, node_ids in self.question_node_map.items()}

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


class MemoryItem:
    """
    MemoryItem 类用于存储与某个动作（action）相关的观察、问题与节点ID的映射。
    """

    def __init__(self, action: str,
                 observation: str,
                 description: str,
                 question_node_pair: Optional[QuestionNodePair] = None,
                 timestamp: Optional[datetime] = None):
        """
        初始化 MemoryItem 对象。

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
        向 MemoryItem 中的 question_node_map 添加新的 question 和 node_ids。

        Args:
            question (str): 问题作为 key。
            node_ids (Optional[Union[str, Set[str]]]): 节点ID，可以是单个字符串或 set。
        """
        self.question_node_pair.add_node_ids(question, node_ids)

    async def run_action_and_update(self, get_graph_func: Callable, llm_extract_func: Callable):
        """
        异步执行动作，更新 Observation 和每个 Node 的 Conclusion。
        如果正则表达式为空，则调用 LLM 提取关键信息。

        Args:
            llm_extract_func (callable, optional): 提供的 LLM 提取关键信息的异步函数。
            get_graph_func (callable): 获取最新图表信息的函数。
        """
        # 执行动作，获取结果
        result = execute_action(self.action)
        self.observation = result

        # 获取当前最新图表信息
        current_graph_obj = get_graph_func()

        # 准备并发任务队列
        tasks = []
        node_mapping = []  # 用于追踪任务和 Node 实例的映射

        for question, node_ids in self.question_node_pair.question_node_map.items():
            for node_id in node_ids:
                # 获取节点对象（Node 实例）
                node_obj = current_graph_obj.get_node(node_id)

                if node_obj.regex:
                    # 使用正则表达式进行匹配
                    task = self.process_regex(result, node_obj.regex)
                else:
                    # 如果没有正则表达式，调用 LLM 提取关键信息
                    if llm_extract_func:
                        task = llm_extract_func(result, question)
                    else:
                        task = self.handle_no_llm_func(question)

                tasks.append(task)
                node_mapping.append(node_obj)

        # 并发执行任务并收集结果
        conclusions = await asyncio.gather(*tasks, return_exceptions=True)

        # 更新每个 Node 对应的结论
        for node_obj, conclusion in zip(node_mapping, conclusions):
            if isinstance(conclusion, Exception):
                node_obj.conclusion = f"发生错误: {str(conclusion)}"
            else:
                node_obj.conclusion = conclusion

        # 更新最后执行时间
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        将 MemoryItem 对象转换为字典格式，便于存储和序列化。

        Returns:
            Dict[str, Any]: 包含动作、观察、描述、问题和时间戳的字典。
        """
        return {
            "action": self.action,
            "observation": self.observation,
            "description": self.description,
            "question_node_pairs": self.question_node_pair.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(item_dict: Dict[str, Any]) -> 'MemoryItem':
        """
        从字典中重建 MemoryItem 对象。

        Args:
            item_dict (Dict[str, Any]): 存储数据的字典。

        Returns:
            MemoryItem: 生成的 MemoryItem 对象。
        """
        timestamp = datetime.fromisoformat(item_dict["timestamp"])
        action = item_dict["action"]
        question_node_pair = QuestionNodePair.from_dict(item_dict["question_node_pairs"])

        return MemoryItem(
            action=action,
            observation=item_dict["observation"],
            description=item_dict["description"],
            question_node_pair=question_node_pair,
            timestamp=timestamp
        )

    async def process_regex(self, result: str, regex: str) -> str:
        """
        使用正则表达式处理结果，并返回匹配的结论。

        Args:
            result (str): 动作执行的结果。
            regex (str): 用于匹配的正则表达式。

        Returns:
            str: 正则匹配到的结论，或者返回匹配失败信息。
        """
        match = re.search(regex, result)
        if match:
            return match.group(0)
        else:
            return f"正则表达式匹配失败: '{result}' 配置的正则: {regex}"

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
    MemoryItemFactory 是一个工厂类，用于根据给定的参数构造 MemoryItem 对象。
    """

    @staticmethod
    def create_memory_item(action: str, observation: str, description: str, question: str,
                           node_ids: Union[str, Set[str]]) -> 'MemoryItem':
        """
        根据传入的参数创建 MemoryItem 对象。

        Args:
            action (str): 动作名称。
            observation (str): 观察内容。
            description (str): 描述信息。
            question (str): 相关的问题。
            node_ids (Union[str, Set[str]]): 与问题关联的节点ID，可以是单个字符串或集合。

        Returns:
            MemoryItem: 创建并返回 MemoryItem 对象。
        """
        # 创建 QuestionNodePair 对象并添加节点ID
        question_node_pair = QuestionNodePair()
        question_node_pair.add_node_ids(question, node_ids)

        # 创建 MemoryItem 对象并添加 question_node_pair
        memory_item = MemoryItem(
            action=action,
            observation=observation,
            description=description,
            question_node_pair=question_node_pair,
            timestamp=datetime.now()
        )

        return memory_item
