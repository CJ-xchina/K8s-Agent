import asyncio
import json
import threading
import time
from typing import Any, Dict, Optional, Callable, List

from bean.memory import MemoryItem  # 假设 MemoryItem 已正确导入


class baseMemory(object):
    """
    MemoryBase 类用于存储 MemoryItem 对象，并提供自动刷新机制。
    每隔 interval_seconds 秒自动刷新 MemoryItem 的 Observation 和 Conclusion。
    使用 action 作为键，以便能够快速查找和更新 MemoryItem。
    """

    def __init__(self, interval_seconds: int, get_graph_func: Callable):
        """
        初始化 MemoryBase，并在创建后立即启动自动刷新。

        Args:
            interval_seconds (int): 自动刷新的时间间隔，单位为秒。
            get_graph_func (Callable): 获取最新图表信息的函数，用于 MemoryItem 的更新。
        """
        self.memory_store: Dict[str, MemoryItem] = {}  # 使用 action 作为键存储 MemoryItem

        # 启动自动刷新线程
        self.start_automatic_refresh(interval_seconds)

        self.get_graph_func = get_graph_func

    def store_data(self, item: MemoryItem):
        """
        存储 MemoryItem 到内存存储中，使用 action 作为键。
        如果 action 已经存在，则覆盖旧的 MemoryItem。

        Args:
            item (MemoryItem): 要存储的 MemoryItem 对象。
        """
        self.memory_store[item.action] = item

    def get_data(self, fields: Optional[List[str]] = None) -> str:
        """
        获取存储的数据，并根据提供的字段返回数据，返回 JSON 格式字符串。
        如果未指定 fields，则返回所有 MemoryItem 数据。

        Args:
            fields (List[str], optional): 要提取的 MemoryItem 属性字段。如果为空，则返回完整的 MemoryItem 数据。

        Returns:
            str: 包含 MemoryItem 数据的 JSON 字符串。
        """
        # 如果未指定 fields，则返回所有 MemoryItem 数据
        result = [self._extract_fields(item, fields) for item in self.memory_store.values()]

        # 将结果转换为 JSON 格式字符串
        return json.dumps(result)

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

    def refresh_all_items(self):
        """
        刷新所有的 MemoryItem，执行动作并更新 Observation 和 Conclusion。
        """
        for action, item in self.memory_store.items():
            print(f"正在刷新 action: {action}")
            # 执行 MemoryItem 的动作并更新数据
            asyncio.run(item.run_action_and_update(self.get_graph_func, None))

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

    def get_memory_item_by_action(self, action: str) -> Optional[MemoryItem]:
        """
        根据 action 查找并返回对应的 MemoryItem。

        Args:
            action (str): 要查找的 action 名称。

        Returns:
            Optional[MemoryItem]: 返回找到的 MemoryItem，如果不存在则返回 None。
        """
        return self.memory_store.get(action, None)

    def remove_memory_item_by_action(self, action: str):
        """
        根据 action 删除对应的 MemoryItem。

        Args:
            action (str): 要删除的 action 名称。
        """
        if action in self.memory_store:
            del self.memory_store[action]
            print(f"已删除 action: {action} 对应的 MemoryItem")
        else:
            print(f"未找到 action: {action} 对应的 MemoryItem")
