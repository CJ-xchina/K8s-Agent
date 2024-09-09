import json
from pathlib import Path

from typing import List, Dict, Optional


class Node:
    def __init__(self, node_id: str, question: str, node_type: str, node_left: int, node_top: int,
                 regex: Optional[str] = None, action: Optional[str] = None, conclusion: Optional[str] = None,
                 description: Optional[str] = None, endpoints: Optional[List[Dict]] = None):
        self.node_id = node_id
        self.question = question
        self.regex = regex
        self.action = action
        self.conclusion = conclusion
        self.description = description
        self.node_type = node_type
        self.node_left = node_left
        self.node_top = node_top
        self.endpoints = endpoints if endpoints is not None else []
        self.edges = []  # 存储从该节点出发的所有边

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

    def to_dict(self):
        """
        将节点转换为字典，方便序列化。
        """
        return {
            "nodeId": self.node_id,
            "question": self.question,
            "regex": self.regex,
            "action": self.action,
            "conclusion": self.conclusion,
            "description": self.description,
            "nodeType": self.node_type,
            "nodeLeft": self.node_left,
            "nodeTop": self.node_top,
            "endpoints": self.endpoints,
            "reachableNodes": self.get_reachable_nodes(),
            "conditions": self.get_node_if_statement()
        }


class Edge:
    def __init__(self, source_node: str, target_node: str, edge_type: str = "endpoint",
                 condition_value: Optional[str] = None):
        self.source_node = source_node
        self.target_node = target_node
        self.edge_type = edge_type
        self.condition_value = condition_value

    def to_dict(self):
        """
        将边转换为字典，方便序列化。
        """
        return {
            "sourceNode": self.source_node,
            "targetNode": self.target_node,
            "type": self.edge_type,
            "condition": self.condition_value
        }


class Graph:
    def __init__(self, start_node_id: str, json_source: Optional[Dict]):
        self.nodes = {}
        self.edges = []
        self.start_node_id = start_node_id
        self.current_node_id = start_node_id

        if json_source:
            # 如果是文件路径，则加载文件内容
            if isinstance(json_source, str) and Path(json_source).is_file():
                with open(json_source, 'r', encoding='utf-8') as file:
                    json_data = json.load(file)
                    self.load_from_json(json_data)
            else:
                # 否则假设传入的是字典
                self.load_from_json(json_source)

    def add_node(self, node: Node):
        """
        将节点添加到图中。
        :param node: 要添加的节点。
        """
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        获取指定ID的节点。
        :param node_id: 节点ID。
        :return: 对应的Node对象或None。
        """
        return self.nodes.get(node_id)

    def add_edge(self, edge: Edge):
        """
        将边添加到图中，并且将边添加到源节点的 `edges` 列表中。
        :param edge: 要添加的边。
        """
        self.edges.append(edge)
        source_node = self.get_node(edge.source_node)
        if source_node:
            source_node.add_edge(edge)

    def get_current_node(self):
        """
        获取当前节点。
        :return: 当前节点。
        """
        return self.get_node(self.current_node_id)

    def get_current_node_if_statement(self) -> List[str]:
        """
        获取当前节点的if语句条件。
        :return: 当前节点的if语句条件列表。
        """
        current_node = self.get_current_node()
        if current_node:
            return current_node.get_node_if_statement()
        return []

    def get_reachable_nodes(self, node_id: str) -> List[str]:
        """
        获取指定节点ID的可达节点。
        :param node_id: 节点ID。
        :return: 可达节点ID的列表。
        """
        node = self.get_node(node_id)
        if node:
            return node.get_reachable_nodes()
        else:
            return []

    def load_from_json(self, json_data: Dict):
        """
        从JSON数据加载图结构。
        :param json_data: 包含图节点和边信息的字典。
        """
        # 加载节点信息
        for node_data in json_data.get("nodes", []):
            node = Node(
                node_id=node_data["id"],
                question=node_data["question"],
                regex=node_data.get("regex"),
                action=node_data.get("action"),
                conclusion=node_data.get("conclusion"),
                description=node_data.get("description"),
                node_type=node_data.get("nodeType"),
                node_left=node_data.get("nodeLeft"),
                node_top=node_data.get("nodeTop"),
                endpoints=node_data.get("endpoints", [])
            )
            self.add_node(node)

        # 加载边信息
        for edge_data in json_data.get("edges", []):
            edge = Edge(
                source_node=edge_data.get("source"),
                target_node=edge_data.get("target"),
                edge_type=edge_data.get("type", "endpoint"),
                condition_value=edge_data.get("value")
            )
            self.add_edge(edge)

    def get_graph_obj(self) -> 'Graph':
        """
        获取图对象本身。
        :return: 图对象。
        """
        return self

    def is_terminal_node(self, node_id: str) -> bool:
        """
        检查给定节点是否为终止节点，即没有转移条件。
        :param node_id: 要检查的节点ID。
        :return: 如果是终止节点返回True，否则返回False。
        """
        node = self.get_node(node_id)
        if node:
            return len(node.get_reachable_nodes()) == 0
        return False

    def is_current_node_terminal(self) -> bool:
        """
        检查当前节点是否为终止节点（即没有转移条件）。
        :return: 如果是终止节点返回True，否则返回False。
        """
        return self.is_terminal_node(self.current_node_id)

    def to_json(self) -> str:
        """
        将整个图对象转换为 JSON 字符串，包含节点和边。
        :return: JSON 字符串。
        """
        graph_data = {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges]
        }
        return json.dumps(graph_data, indent=4)

    def get_conclusion_by_id(self, node_id: str):
        node = self.get_node(node_id)
        return node.conclusion


    def jump_to_node_by_condition(self, condition_value: str):
        """
        根据传入的条件值，让 current_node_id 跳转到对应的目标节点。
        如果当前节点没有对应的条件值，则抛出异常。
        :param condition_value: 条件值，用于选择下一步跳转的节点。
        """
        current_node = self.get_current_node()
        if not current_node:
            raise ValueError(f"当前节点 ID {self.current_node_id} 不存在。")

        for edge in current_node.edges:
            if edge.condition_value == condition_value:
                self.current_node_id = edge.target_node
                next_node = self.get_node(self.current_node_id)
                if next_node:
                    next_node.is_visited = True
                print(f"跳转到节点 {self.current_node_id}。")
                return

        raise ValueError(f"在节点 {current_node.node_id} 中没有找到匹配的条件值: {condition_value}。")
