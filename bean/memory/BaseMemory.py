import asyncio
import heapq
import threading
import time
from typing import Dict, Optional, List, Tuple

from bean.memory.NodeMemoryItem import NodeMemoryItem
from bean.memory.RecordMemoryItem import RecordMemoryItem
from bean.stage.base.BaseStage import BaseStage


class BaseMemory:
    """
    MemoryBase 类用于存储 NodeMemoryItem 对象，并提供自动刷新机制。
    每隔 interval_seconds 秒自动刷新 NodeMemoryItem 的 Observation 和 Conclusion。
    使用优先队列存储 (timestamp, action)，并使用 action_map 存储 {action: NodeMemoryItem} 的映射。
    """

    def __init__(self, interval_seconds: int, extract_stage: BaseStage, conclusion_stage: BaseStage):
        """
        初始化 MemoryBase，并在创建后立即启动自动刷新。

        Args:
            interval_seconds (int): 自动刷新的时间间隔，单位为秒。
        """
        # 优先队列，存储 (timestamp, action)，保证按时间排序
        self.memory_store: List[Tuple[float, str]] = []  # 使用优先队列存储 (timestamp, action)
        # 用于快速查找的 action -> NodeMemoryItem 的映射表
        self.action_map: Dict[str, NodeMemoryItem] = {}

        # 存储每一个记录映射 id -> RecordMemoryItem
        self.record_map: Dict[str, RecordMemoryItem] = {}

        # 设置与大模型的交互阶段
        self.extract_stage = extract_stage
        self.conclusion_stage = conclusion_stage

        # 启动自动刷新线程
        self.start_automatic_refresh(interval_seconds)

    def store_data(self, item: NodeMemoryItem):
        """
        存储 NodeMemoryItem 到优先队列中，并使用 action 作为键来标识。
        如果 action 已经存在，则在该 action 的 QuestionNodePair 中添加新的 question 和 node_ids。

        Args:
            item (NodeMemoryItem): 要存储的 NodeMemoryItem 对象。
        """
        if item.action in self.action_map:
            existing_item = self.action_map[item.action]

            # 将新的 question 和 node_ids 添加到现有的 NodeMemoryItem 中
            for question, node_ids in item.question_node_pair.question_node_map.items():
                existing_item.add_question_node_pair(question, node_ids)

            # 更新现有的 NodeMemoryItem 的 timestamp
            existing_item.timestamp = item.timestamp
        else:
            # 如果不存在这个 action，直接添加新的 NodeMemoryItem
            self.action_map[item.action] = item

        # 更新优先队列（确保最新的时间戳优先）
        heapq.heappush(self.memory_store, (-item.timestamp.timestamp(), item.action))

    def store_record(self, record_item: RecordMemoryItem):
        """
        存储 RecordMemoryItem 到 record_map 中，使用 id 作为键标识。

        Args:
            record_item (RecordMemoryItem): 要存储的 RecordMemoryItem 对象。
        """
        record_id = record_item.id
        if record_id in self.record_map:
            print(f"Record with ID {record_id} 已存在，更新现有记录。")
        else:
            print(f"存储新的 RecordMemoryItem，ID: {record_id}")

        # 存储或更新 record_map 中的 RecordMemoryItem
        self.record_map[record_id] = record_item

    def refresh_all_items(self):
        """
        按照优先队列顺序（时间最新的在最前）刷新所有的 NodeMemoryItem，
        执行动作并更新 Observation 和 Conclusion。
        """
        temp_store = []

        # 逐个弹出优先队列中的元素，时间最新的 NodeMemoryItem 最先处理
        while self.memory_store:
            _, action = heapq.heappop(self.memory_store)

            # 从 action_map 中获取对应的 NodeMemoryItem
            item = self.action_map.get(action)
            if item:
                try:
                    print(f"正在刷新 action: {item.action}")
                    # 异步执行 NodeMemoryItem 的动作并更新数据
                    asyncio.run(self._run_action_and_update(item))

                    # 将处理完的元素存储到临时列表，以便之后重新放回队列
                    temp_store.append((-item.timestamp.timestamp(), item.action))

                except Exception as e:
                    print(f"刷新 item: {item.action} 时出错: {e}")

        # 将处理过的 NodeMemoryItem 重新放回优先队列
        for entry in temp_store:
            heapq.heappush(self.memory_store, entry)

    async def _run_action_and_update(self, item: NodeMemoryItem):
        """
        异步执行 NodeMemoryItem 的动作并更新 Observation 和 Conclusion。
        """
        await item.run_action_and_update(self.extract_stage, self.conclusion_stage)

    def start_automatic_refresh(self, interval_seconds: int):
        """
        定时刷新 NodeMemoryItem 的数据。每隔 interval_seconds 秒执行一次刷新。

        Args:
            interval_seconds (int): 刷新间隔，单位为秒。
        """

        def refresh_loop():
            while True:
                time.sleep(interval_seconds)
                self.refresh_all_items()

        # 启动后台线程，定期刷新 NodeMemoryItem
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()

