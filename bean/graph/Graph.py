import json
from typing import List, Dict, Optional, Union
from typing import List, Dict, Optional


class Node:
    def __init__(self, node_id: str, node_type: str, action: Optional[str] = None, if_statement: Optional[str] = None):
        self.node_id = node_id
        self.node_type = node_type
        self.action = action
        self.if_statement = if_statement
        self.transitions = {}

    def add_transition(self, condition: str, target_node: str):
        self.transitions[condition] = target_node

    def get_reachable_nodes(self) -> List[str]:
        return list(self.transitions.values())

    def __repr__(self):
        return f"Node(id={self.node_id}, type={self.node_type}, action={self.action}, transitions={self.transitions})"


class Graph:
    def __init__(self, start_node_id, json_source):
        """
        Initialize the Graph object. You can pass a JSON string, a file path, or a dictionary.

        :param json_source: JSON string, file path to a JSON file, or a dictionary containing the graph data.
        """
        self.nodes = {}

        self.start_node_id = start_node_id

        self.current_node_id = start_node_id
        if json_source:
            if isinstance(json_source, str):
                try:
                    # Attempt to load as file path
                    with open(json_source, 'r', encoding='utf-8') as file:
                        json_data = json.load(file)
                        self.load_from_json(json_data)
                except FileNotFoundError:
                    # If it's not a valid file path, treat it as JSON string
                    json_data = json.loads(json_source)
                    self.load_from_json(json_data)
            elif isinstance(json_source, Dict):
                self.load_from_json(json_source)

        self.traverse_graph(self.start_node_id)

    def traverse_graph(self, start_node_id: str):
        """
        从指定节点开始遍历图。这可以扩展为与 LLM 聊天或其他系统进行交互。

        :param start_node_id: 起始节点的 ID。
        """
        current_node_id = start_node_id
        while current_node_id:
            node = self.get_node(current_node_id)
            if not node:
                print(f"未找到节点 {current_node_id}。")
                break

            # 简单起见，遵循 'true' 转移
            next_node_id = node.transitions.get('true')
            if not next_node_id:
                print(f"路径在节点 {current_node_id} 处结束。")
                break

            current_node_id = next_node_id

    def add_node(self, node: Node):
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def get_reachable_nodes(self, node_id: str) -> List[str]:
        node = self.get_node(node_id)
        if node:
            return node.get_reachable_nodes()
        else:
            return []

    def load_from_json(self, json_data: Dict):
        for node_data in json_data.get("nodes", []):
            node = Node(
                node_id=node_data["id"],
                node_type=node_data["type"],
                action=node_data.get("action"),
                if_statement=node_data.get("if_statement")
            )
            self.add_node(node)
            if "true_transition" in node_data:
                node.add_transition("true", node_data["true_transition"])
            if "false_transition" in node_data:
                node.add_transition("false", node_data["false_transition"])

    def find_isolated_nodes(self):
        isolated_nodes = []
        all_node_ids = set(self.nodes.keys())
        connected_nodes = set()

        # Check for nodes that have outgoing connections (out-degree)
        for node in self.nodes.values():
            for target_node_id in node.get_reachable_nodes():
                connected_nodes.add(target_node_id)
            if node.get_reachable_nodes():
                connected_nodes.add(node.node_id)

        # Nodes that have neither incoming nor outgoing connections are isolated
        isolated_nodes = all_node_ids - connected_nodes

        if isolated_nodes:
            print("Isolated nodes found:")
            for node_id in isolated_nodes:
                print(f"Node ID: {node_id}")
        else:
            print("No isolated nodes found.")

    def __repr__(self):
        return f"Graph(nodes={self.nodes})"


if __name__ == "__main__":
    # Initialize with a file path
    gr = Graph("../../resources/pod_graph.json")

    # Alternatively, initialize with a JSON string
    # json_string = '{"nodes": [{"id": "1", "type": "start", ...}]}'
    # gr = Graph(json_string)

    gr.find_isolated_nodes()
    print("ok")
