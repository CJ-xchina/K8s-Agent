from typing import List, Optional

from bean.graph.Edge import Edge
from bean.graph.Node import Node


class Graph:
    def __init__(self, graph_id: str, category: str = "", purpose: str = "", name: str = ""):
        self.nodes = {}
        self.edges = []
        self.start_node_id = "1"
        self.current_node_id = "1"
        self.category = category
        self.purpose = purpose
        self.name = name
        self.graph_id = graph_id
        self.position = [0, 0]
        self.zoom = 1.0
        self.viewport = {"x": 0, "y": 0, "zoom": 1.0}

        # 节点执行顺序, 用于回退
        self.work_flow = []

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

    def to_json(self) -> dict:
        """将整个图对象转换为所需的 JSON 字典，包含节点和边，格式与要求一致。"""
        return {
            self.graph_id: {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "edges": [edge.to_dict() for edge in self.edges],
                "position": self.position,
                "zoom": self.zoom,
                "viewport": self.viewport
            }
        }

    @staticmethod
    def from_flow_data_map(graph_id: str, flow_data_map: dict, name: str = "", category: str = "", purpose: str = ""):
        """从 flowDataMap 创建图对象，并设置 name, category, purpose"""
        graph = Graph(graph_id=graph_id, name=name, category=category, purpose=purpose)

        # 设置位置和缩放
        graph.position = flow_data_map.get("position", [0, 0])
        graph.zoom = flow_data_map.get("zoom", 1.0)
        graph.viewport = flow_data_map.get("viewport", {"x": 0, "y": 0, "zoom": 1.0})

        # 初始化 start_node_id 和 current_node_id
        graph.start_node_id = None
        graph.current_node_id = None

        # 加载节点信息，找到 type 为 "input" 的节点
        for node_data in flow_data_map.get("nodes", []):
            node = Node(
                node_id=node_data["id"],
                question=node_data.get("data", {}).get("question", ""),
                regex=node_data.get("data", {}).get("regex", ""),
                action=node_data.get("data", {}).get("action", ""),
                description=node_data.get("data", {}).get("description", ""),
                node_type=node_data.get("type", "default"),
                node_left=node_data["position"]["x"],
                node_top=node_data["position"]["y"],
                parent_node=node_data.get("parentNode", None)
            )
            graph.add_node(node)

            # 如果节点类型为 "input"，则将其设置为起始节点
            if node.node_type == "input":
                graph.start_node_id = node.node_id
                graph.current_node_id = node.node_id

        # 如果没有找到 "input" 类型的节点，抛出异常或处理为 None
        if graph.start_node_id is None:
            raise ValueError(f"Graph {graph_id} does not contain a node with type 'input'")

        # 加载边信息
        for edge_data in flow_data_map.get("edges", []):
            edge = Edge(
                edge_id=edge_data["id"],
                source_node=edge_data["source"],
                target_node=edge_data["target"],
                edge_type=edge_data.get("type", "default"),
                condition_value=edge_data["data"].get("label", ""),
                source_Handle=edge_data.get("sourceHandle", ""),
                target_Handle=edge_data.get("targetHandle", "")
            )
            graph.add_edge(edge)

        return graph

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

    def get_category(self) -> str:
        """
        获取流程图的分类。
        :return: 流程图的分类。
        """
        return self.category

    def get_purpose(self) -> str:
        """
        获取流程图的目的。
        :return: 流程图的目的。
        """
        return self.purpose

    def get_name(self) -> str:
        """
        获取流程图名称
        :return:  流程图名称
        """
        return self.name
