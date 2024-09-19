import uuid
from typing import List, Dict, Any


class Workflow:
    def __init__(self, current_node_id: str, context: Dict[str, Any] = None):
        """
        初始化 Workflow 对象。

        参数:
            workflow_id (str): 工作流的唯一标识符。
            current_node_id (str): 当前执行的节点 ID。
            context (Dict[str, Any], optional): 工作流的上下文信息。
        """
        self.workflow_id = str(uuid.uuid4())
        self.current_node_id = current_node_id
        self.history: List[str] = []  # 存储已执行的节点 ID
        self.context: Dict[str, Any] = context if context else {}

    def update_context(self, key: str, value: Any):
        """
        更新上下文信息。

        参数:
            key (str): 键。
            value (Any): 值。
        """
        self.context[key] = value

    def add_to_history(self, node_id: str):
        """
        将节点添加到执行历史中。

        参数:
            node_id (str): 节点 ID。
        """
        self.history.append(node_id)

    def set_current_node(self, node_id: str):
        """
        设置当前节点 ID。

        参数:
            node_id (str): 节点 ID。
        """
        self.current_node_id = node_id
