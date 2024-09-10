from typing import Optional


class Edge:
    def __init__(self, edge_id: str, source_node: str, target_node: str, edge_type: str,
                 condition_value: Optional[str] = ""):
        self.edge_id = edge_id
        self.source_node = source_node
        self.target_node = target_node
        self.edge_type = edge_type
        self.condition_value = condition_value  # Store condition_value internally

    def to_dict(self):
        """
        将边转换为字典，方便序列化，并将 condition_value 转换为 data['label'].
        """
        return {
            "id": self.edge_id,  # Edge ID like "source->target"
            "type": self.edge_type,
            "source": self.source_node,
            "target": self.target_node,
            "data": {
                "label": self.condition_value  # Construct data['label'] from condition_value
            }
        }
