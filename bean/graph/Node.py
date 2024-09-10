from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

from bean.graph.Edge import Edge


# 定义节点状态枚举
class NodeStatusEnum(Enum):
    WAITING = "waiting"
    EXECUTING = "executing"
    COMPLETED = "completed"


class Node:
    def __init__(self, node_id: str, question: str, node_type: str, node_left: int, node_top: int,
                 regex: Optional[str] = "", action: Optional[str] = "", conclusion: Optional[str] = "",
                 description: Optional[str] = ""):
        self.node_id = node_id
        self.question = question
        self.regex = regex
        self.action = action
        self.conclusion = conclusion
        self.description = description
        self.node_type = node_type
        self.node_left = node_left
        self.node_top = node_top
        self.edges = []  # 存储从该节点出发的所有边

        # 新增字段
        self.status = NodeStatusEnum.WAITING  # 默认状态为等待
        self.start_time = ""  # 开始执行时间，默认为空
        self.end_time = ""  # 结束执行时间，默认为空
        self.llm_call_count = 0  # 调用LLM总次数，默认为0

    def add_edge(self, edge: 'Edge'):
        """
        向节点添加边。
        :param edge: 边对象。
        """
        self.edges.append(edge)

    def get_reachable_nodes(self) -> List[str]:
        """
        获取节点可达的目标节点列表。
        :return: 目标节点ID的列表。
        """
        return [edge.target_node for edge in self.edges]

    def get_node_if_statement(self) -> List[str]:
        """
        返回一个包含所有条件值（condition_value）的数组。
        :return: 条件值的列表。
        """
        return [edge.condition_value for edge in self.edges if edge.condition_value]

    def start_execution(self):
        """
        设置节点为执行状态，并记录开始时间。
        """
        self.status = NodeStatusEnum.EXECUTING
        self.start_time = datetime.now()

    def complete_execution(self):
        """
        设置节点为完成状态，并记录结束时间。
        """
        self.status = NodeStatusEnum.COMPLETED
        self.end_time = datetime.now()

    def to_dict(self):
        """
        将节点转换为字典，方便序列化，包含所有节点属性（不包括 edges 和 endpoints）
        """
        return {
            "id": self.node_id,
            "data": {
                "question": self.question,
                "regex": self.regex,
                "action": self.action,
                "conclusion": self.conclusion,
                "description": self.description,
                "status": self.status.value,
                "startTime": self.start_time.isoformat() if self.start_time else "",
                "endTime": self.end_time.isoformat() if self.end_time else "",
                "llmCallCount": self.llm_call_count
            },
            "type": self.node_type,
            "position": {
                "x": self.node_left,
                "y": self.node_top
            }
        }
