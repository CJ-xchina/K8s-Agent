import json
from typing import List, Dict, Optional

from bean.graph.Edge import Edge
from bean.graph.Node import Node


class Graph:
    def __init__(self, json_source: str):
        self.nodes = {}
        self.edges = []
        self.start_node_id = "1"
        self.current_node_id = "1"

        if json_source:
            # 如果是文件路径，则加载文件内容
            if isinstance(json_source, str) and Path(json_source).is_file():
                with open(json_source, 'r', encoding='utf-8') as file:
                    json_data = json.load(file)
                    self.load_from_json(json_data)
            else:
                json_map = json.loads(json_source)
                self.load_from_json(json_map)
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

        only_one_input = False
        # 加载节点信息
        for node_data in json_data.get("nodes", []):

            node = Node(
                node_id=node_data["id"],
                question=node_data["data"].get("question", ""),
                regex=node_data["data"].get("regex", ""),
                action=node_data["data"].get("action", ""),
                description=node_data["data"].get("description", ""),
                node_type=node_data.get("type", "default"),
                node_left=node_data["position"].get("x"),
                node_top=node_data["position"].get("y")
            )

            if node.node_type == "input":
                if only_one_input:
                    raise Exception("只能有一个入口")
                only_one_input = True
                self.current_node_id = node.node_id
                self.start_node_id = node.node_id
            self.add_node(node)

        # 加载边信息
        for edge_data in json_data.get("edges", []):
            edge = Edge(
                edge_id=edge_data["id"],
                source_node=edge_data["source"],
                target_node=edge_data["target"],
                edge_type=edge_data.get("type", "default"),
                condition_value=edge_data["data"]["label"],
                source_Handle=edge_data["sourceHandle"],
                target_Handle=edge_data["targetHandle"]
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
        return json.dumps(graph_data, indent=5, ensure_ascii=False)

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


from pathlib import Path


def main(json_file_path: str):
    # Check if the file exists
    if not Path(json_file_path).is_file():
        print(f"Error: The file {json_file_path} does not exist.")
        return

    # Load the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    # Create a Graph instance, assuming start_node_id is "1" or any valid start node in the JSON.
    start_node_id = json_data["nodes"][0]["id"]  # Assuming first node as start node
    graph = Graph(json_source=json_data)

    # Output the graph as JSON for verification
    graph_json = graph.to_json()
    print(graph_json)


if __name__ == "__main__":
    json_file_path = "../../resources/pod-graph.json"
    main(json_file_path)
