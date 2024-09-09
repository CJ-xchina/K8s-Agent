import asyncio
import json
import threading
import time
import heapq
from typing import Any, Dict, Optional, Callable, List, Tuple

from bean.memory.MemoryItem import MemoryItem


class baseMemory(object):
    """
    MemoryBase 类用于存储 MemoryItem 对象，并提供自动刷新机制。
    每隔 interval_seconds 秒自动刷新 MemoryItem 的 Observation 和 Conclusion。
    使用优先队列存储 (timestamp, action)，并使用 action_map 存储 {action: MemoryItem} 的映射。
    """

    def __init__(self, interval_seconds: int, get_graph_func: Callable):
        """
        初始化 MemoryBase，并在创建后立即启动自动刷新。

        Args:
            interval_seconds (int): 自动刷新的时间间隔，单位为秒。
            get_graph_func (Callable): 获取最新图表信息的函数，用于 MemoryItem 的更新。
        """
        # 优先队列，存储 (timestamp, action)，保证按时间排序
        self.memory_store: List[Tuple[float, str]] = []  # 使用优先队列存储 (timestamp, action)
        # 用于快速查找的 action -> MemoryItem 的映射表
        self.action_map: Dict[str, MemoryItem] = {}  # 快速查找的action -> MemoryItem 映射表

        # 启动自动刷新线程
        self.start_automatic_refresh(interval_seconds)

        self.get_graph_func = get_graph_func

    def store_data(self, item: MemoryItem):
        """
        存储 MemoryItem 到优先队列中，并使用 action 作为键来标识。
        如果 action 已经存在，则在该 action 的 QuestionNodePair 中添加新的 question 和 node_ids。

        Args:
            item (MemoryItem): 要存储的 MemoryItem 对象。
        """
        # 如果该 action 已经存在，则更新旧的 MemoryItem 而不是直接替换
        if item.action in self.action_map:
            existing_item = self.action_map[item.action]

            # 将新的 question 和 node_ids 添加到现有的 MemoryItem 中
            for question, node_ids in item.question_node_pair.question_node_map.items():
                existing_item.add_question_node_pair(question, node_ids)

            # 更新现有的 MemoryItem 的 timestamp
            existing_item.timestamp = item.timestamp
        else:
            # 如果不存在这个 action，直接添加新的 MemoryItem
            self.action_map[item.action] = item

        # 将 MemoryItem 添加到优先队列（使用负时间戳确保最新时间在前）
        heapq.heappush(self.memory_store, (-item.timestamp.timestamp(), item.action))

    def refresh_all_items(self):
        """
        按照优先队列顺序（时间最新的在最前）刷新所有的 MemoryItem，
        执行动作并更新 Observation 和 Conclusion。
        """
        temp_store = []

        # 逐个弹出优先队列中的元素，时间最新的 MemoryItem 最先处理
        while self.memory_store:
            # 从优先队列中弹出时间最近的元素
            _, action = heapq.heappop(self.memory_store)

            # 从 action_map 中获取对应的 MemoryItem
            item = self.action_map.get(action)
            if item:
                print(f"正在刷新 action: {item.action}")
                # 执行 MemoryItem 的动作并更新数据
                asyncio.run(item.run_action_and_update(self.get_graph_func, None))

                # 将处理完的元素存储到临时列表，以便之后重新放回队列
                temp_store.append((-item.timestamp.timestamp(), item.action))

        # 将处理过的 MemoryItem 重新放回优先队列
        for entry in temp_store:
            heapq.heappush(self.memory_store, entry)

    def _extract_fields(self, item: MemoryItem, fields: Optional[List[str]]) -> Dict[str, Any]:
        """
        从 MemoryItem 中提取指定字段，如果没有指定字段则返回完整的数据。

        Args:
            item (MemoryItem): 要提取数据的 MemoryItem 对象。
            fields (List[str], optional): 需要提取的字段列表。

        Returns:
            Dict[str, Any]: 包含提取字段或完整 MemoryItem 的字典。
        """
        if not fields:
            return item.to_dict()

        extracted_data = {}
        item_dict = item.to_dict()

        for field in fields:
            if field in item_dict:
                extracted_data[field] = item_dict[field]

        return extracted_data

    def start_automatic_refresh(self, interval_seconds: int):
        """
        定时刷新 MemoryItem 的数据。每隔 interval_seconds 秒执行一次刷新。

        Args:
            interval_seconds (int): 刷新间隔，单位为秒。
        """

        def refresh_loop():
            while True:
                time.sleep(interval_seconds)
                self.refresh_all_items()

        # 启动后台线程，定期刷新 MemoryItem
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()

    def get_data(self, fields: Optional[List[str]] = None) -> str:
        """
        获取存储的数据，并根据提供的字段返回数据，返回 JSON 格式字符串。
        如果未指定 fields，则返回所有 MemoryItem 数据。

        Args:
            fields (List[str], optional): 要提取的 MemoryItem 属性字段。如果为空，则返回完整的 MemoryItem 数据。

        Returns:
            str: 包含 MemoryItem 数据的 JSON 字符串。
        """
        result = []
        for action in self.action_map:
            item = self.action_map[action]
            result.append(self._extract_fields(item, fields))

        # 将结果转换为 JSON 格式字符串
        return json.dumps(result)

    def get_memory_item_by_action(self, action: str) -> MemoryItem:
        """
        根据 action 查找并返回对应的 MemoryItem。

        Args:
            action (str): 要查找的 action 名称。

        Returns:
            Optional[MemoryItem]: 返回找到的 MemoryItem，如果不存在则返回 None。
        """
        return self.action_map.get(action)

    def remove_memory_item_by_action(self, action: str):
        """
        根据 action 删除对应的 MemoryItem。

        Args:
            action (str): 要删除的 action 名称。
        """
        # 从优先队列和 action_map 中删除 MemoryItem
        self.memory_store = [entry for entry in self.memory_store if entry[1] != action]
        if action in self.action_map:
            del self.action_map[action]
            print(f"已删除 action: {action} 对应的 MemoryItem")
        else:
            print(f"未找到 action: {action} 对应的 MemoryItem")

    def get_all_summaries(self) -> str:
        """
        获取所有 MemoryItem 的 Action、Description、Question 以及其对应的 NodeId 和 Conclusion。
        返回格式化的字符串，按你要求的格式输出。
        """
        summary = []
        for action, item in self.action_map.items():
            action_summary = f"执行指令：{item.action} 这条指令的作用是: {item.description}"

            # 构建每个 question 和 node_id 的总结
            question_summaries = []
            for question, node_ids in item.question_node_pair.question_node_map.items():
                node_conclusions = [self.get_node_conclusion(node_id) for node_id in node_ids]
                question_summaries.append(f"问题：{question} 答案：{', '.join(node_conclusions)}")

            # 将 action_summary 和 question_summaries 整合
            question_summary = " ".join(question_summaries)
            summary.append(action_summary + " " + question_summary)

        # 返回汇总的字符串
        return "\n".join(summary)

    def get_node_conclusion(self, node_id: str) -> str:
        graph = self.get_graph_func

        return graph.get_conclusion_by_id(node_id)

