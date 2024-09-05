class LlmChatGraph(Graph):
    def __init__(self, start_node_id, json_source):
        """
        初始化 LlmChatGraph 对象。可以传入 JSON 字符串、文件路径或字典来加载图数据。

        :param json_source: JSON 字符串、指向 JSON 文件的路径，或包含图数据的字典。
        :param start_node_id: 初始节点的 ID。
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

    def update_current_node(self, condition_value: str) -> str:
        """
        根据条件值更新 current_node_id。

        :param condition_value: 用于匹配转换条件的值。
        :return: 更新后的节点 ID 或错误信息。
        """
        node = self.get_node(self.current_node_id)
        if not node:
            return f"当前节点 {self.current_node_id} 不存在。"

        # 在当前节点的转移条件中查找匹配的条件值
        for condition, target_node in node.transitions:
            if condition == condition_value:
                self.current_node_id = target_node
                return f"节点已更新为: {self.current_node_id}"

        return f"在节点 {self.current_node_id} 中找不到匹配的条件 {condition_value}。"
