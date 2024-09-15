from datetime import datetime
from enum import Enum
from typing import List, Optional

from bean.graph.Edge import Edge


# 定义节点状态枚举
class NodeStatusEnum(Enum):
    WAITING = "waiting"
    EXECUTING = "executing"
    COMPLETED = "completed"

class Node:
    def __init__(self, node_id: str, question: str, node_type: str, node_left: int, node_top: int,
                 regex: Optional[str] = "", action: Optional[str] = "", conclusion: Optional[str] = "",
                 description: Optional[str] = "", parent_node: Optional[str] = ""):
        # 前端传入的固定参数
        self.node_id = node_id
        self.question = question
        self.regex = regex
        self.action = action
        self.description = description
        self.node_type = node_type
        self.node_left = node_left
        self.node_top = node_top
        self.edges = []  # 存储从该节点出发的所有边
        self.parent_node = parent_node  # default对应组关系

        # 执行时需要修改的参数
        self.status = NodeStatusEnum.WAITING  # 默认状态为等待
        self.start_time = ""  # 开始执行时间，默认为空
        self.end_time = ""  # 结束执行时间，默认为空
        self.llm_call_count = 0  # 调用LLM总次数，默认为0
        self.conclusion = conclusion

    def __hash__(self):
        """
        通过 node_id 生成唯一哈希值。
        """
        return hash(self.node_id)

    def __eq__(self, other):
        """
        判断节点是否相等，基于 node_id。
        """
        if isinstance(other, Node):
            return self.node_id == other.node_id
        return False

    # 其他方法保持不变
    def add_edge(self, edge: 'Edge'):
        self.edges.append(edge)

    def get_reachable_nodes(self) -> List[str]:
        return [edge.target_node for edge in self.edges]

    def get_node_if_statement(self) -> List[str]:
        return [edge.condition_value for edge in self.edges if edge.condition_value]

    def start_execution(self):
        self.status = NodeStatusEnum.EXECUTING
        self.start_time = datetime.now()

    def complete_execution(self):
        self.status = NodeStatusEnum.COMPLETED
        self.end_time = datetime.now()

    def get_execution_summary(self):
        return f"""
        为了解决问题{self.question}, 执行了指令{self.action},该条指令的目的是{self.description},通过观察思考问题的最终结论是:{self.conclusion}
        \n
        """

    def get_error_summary(self):
        return f"""
        存在问题, 问题出现的故障描述如下:{self.description}
        \n
        """

    def to_dict(self):
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
            },
            "parentNode": self.parent_node
        }

