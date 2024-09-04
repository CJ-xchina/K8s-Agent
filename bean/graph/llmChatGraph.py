from bean.graph.Graph import Graph


class LlmChatGraph(Graph):
    def __init__(self, start_node_id, json_source):
        """
        初始化 LlmChatGraph 对象。可以传入 JSON 字符串、文件路径或字典来加载图数据。

        :param json_source: JSON 字符串、指向 JSON 文件的路径，或包含图数据的字典。
        :param start_node_id: 初始节点的 ID，可选参数。
        """
        super().__init__(start_node_id, json_source)

    def get_current_node_details(self) -> str:
        return self.get_node_details(self.current_node_id)

    def get_node_details(self, node_id: str) -> str:
        """
        获取节点的详细信息并以字符串形式返回。

        :param node_id: 节点的 ID。
        :return: 包含节点详细信息的字符串。
        """
        node = self.get_node(node_id)
        if node:
            return self._format_node_details(node)
        else:
            return f"节点 {node_id} 不存在。"

    def _format_node_details(self, node) -> str:
        """
        格式化节点详细信息。

        :param node: 节点对象。
        :return: 格式化后的节点详细信息字符串。
        """
        return f" {node.if_statement} ?\n 建议执行的指令或动作: {node.action}"

    def get_node_details_by_condition(self, condition: str) -> str:
        """
        根据节点 ID 和条件获取跳转后的节点详细信息。

        :param condition: 跳转条件。
        :return: 跳转后的节点详细信息，如果条件不成立或节点不存在，则返回相关信息。
        """
        node_id = self.current_node_id
        node = self.get_node(node_id)
        if not node:
            raise ValueError(f"节点 {node_id} 不存在。")

        # 检查节点类型是否为 "end"
        if node.node_type == "end":
            raise ValueError(f"节点 {node_id} 是一个终止节点，不能跳转到其他节点！")

        next_node_id = node.transitions.get(condition)
        if not next_node_id:
            raise ValueError(f"节点 {node_id} 下不存在符合条件 '{condition}' 的跳转。")

        self.current_node_id = next_node_id
        return self.get_node_details(next_node_id)
