import json

# 原始 JSON 数据
json_data = {
    "nodes": [
        # 这里插入你给定的JSON数据
    ]
}

# 目标格式转换函数
def process_json_data(json_data):
    processed_nodes = []
    processed_edges = []

    for node in json_data.get("nodes", []):
        # 处理节点信息
        processed_node = {
            "id": node["id"],
            "question": node.get("if_statement"),
            "regex": node.get("regex"),
            "action": node.get("action")
        }

        # 添加节点信息到 nodes 列表
        processed_nodes.append(processed_node)

        # 处理边信息 (true_transition 和 false_transition)
        if node.get("true_transition"):
            processed_edges.append({
                "source": node["id"],
                "target": node["true_transition"],
                "value": "true"
            })
        if node.get("false_transition"):
            processed_edges.append({
                "source": node["id"],
                "target": node["false_transition"],
                "value": "false"
            })

    return {
        "nodes": processed_nodes,
        "edges": processed_edges
    }

# 加载 JSON 数据（假设文件路径为 pod_graph.json）
json_source = "./pod_graph.json"
with open(json_source, 'r', encoding='utf-8') as file:
    json_data = json.load(file)

# 处理后的数据
processed_data = process_json_data(json_data)

# 将结果存储到 graph.json 文件中
output_file = "./graph.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, ensure_ascii=False, indent=4)

print(f"Processed data has been saved to {output_file}")
