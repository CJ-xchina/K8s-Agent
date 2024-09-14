from bean.graph.Graph import Graph


class GraphManager:
    def __init__(self):
        self.graphs = {}  # 存储图的字典，key 为图的 id，value 为 Graph 对象
        self.tree_relationships = {}  # 存储树结构关系

    def add_graph(self, graph: Graph):
        self.graphs[graph.graph_id] = graph

    def add_tree_relationship(self, tree_data: list):
        for tree in tree_data:
            self.tree_relationships[tree['id']] = {
                "label": tree['label'],
                "children": [
                    {
                        "id": child['id'],
                        "name": child['name'],
                        "category": child['category'],
                        "purpose": child['purpose']
                    }
                    for child in tree.get('children', [])
                ]
            }

    def to_json(self) -> dict:
        return {
            "flowDataMap": [
                [graph_id, graph.to_json()] for graph_id, graph in self.graphs.items()
            ],
            "treeData": [
                {
                    "id": tree_id,
                    "label": tree['label'],
                    "children": tree['children']
                } for tree_id, tree in self.tree_relationships.items()
            ]
        }

    @staticmethod
    def from_data(json_data: dict):
        manager = GraphManager()

        # 构建一个字典以快速查找 treeData 中的图信息
        tree_info_map = {}
        for tree in json_data.get("treeData", []):
            for child in tree.get("children", []):
                tree_info_map[child['id']] = {
                    "name": child['name'],
                    "category": child['category'],
                    "purpose": child['purpose']
                }

        # 解析 flowDataMap，并根据 treeData 进行图的信息补充
        for flow_data_map in json_data.get("flowDataMap", []):
            graph_id = flow_data_map[0]
            flow_data = flow_data_map[1]

            # 从 tree_info_map 中获取与该图相关的 name, category, purpose
            graph_info = tree_info_map.get(graph_id, {})
            graph_name = graph_info.get("name", "")
            graph_category = graph_info.get("category", "")
            graph_purpose = graph_info.get("purpose", "")

            # 构建 Graph 对象
            graph = Graph.from_flow_data_map(graph_id, flow_data, graph_name, graph_category, graph_purpose)
            manager.add_graph(graph)

        # 解析 treeData 并添加到 GraphManager
        tree_data = json_data.get("treeData", [])
        manager.add_tree_relationship(tree_data)

        return manager

