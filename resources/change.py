import json

# 从指定文件中读取 JSON 数据
def read_json(input_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# 将处理后的 JSON 数据写入指定文件
def write_json(output_file, data):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 示例输入输出文件路径
input_file = 'graph.json'  # 输入文件路径
output_file = 'pod-graph.json'  # 输出文件路径

# 从输入文件读取数据
data = read_json(input_file)

# 将节点转换为字典，方便访问
node_ids = {node["id"]: node for node in data["nodes"]}

# 找出有出边和入边的节点（用于判断起始节点和终止节点）
nodes_with_outgoing_edges = {edge["source"] for edge in data["edges"]}
nodes_with_incoming_edges = {edge["target"] for edge in data["edges"]}

# 设置简单的网格布局来分配节点位置
x, y = 0, 0
step_x, step_y = 200, 200

# 1. 处理节点类型和位置，并添加 'data' 字段
for node in data["nodes"]:
    node["data"] = {
        "question": node.get("question", "") or "",
        "regex": node.get("regex", "") or "",
        "action": node.get("action", "") or "",
        "description": node.get("description", "") or ""
    }
    del node["question"], node["regex"], node["action"]

    # 判断节点类型：起始节点、终止节点、默认节点
    if node["id"] not in nodes_with_incoming_edges:  # 没有入边的节点是起始节点
        node["type"] = "input"
    elif node["id"] not in nodes_with_outgoing_edges:  # 没有出边的节点是终止节点
        node["type"] = "output"
    else:
        node["type"] = "default"

    # 设置节点的位置信息
    node["position"] = {"x": x, "y": y}
    x += step_x  # 每个节点在 x 方向增加间距
    if x > 800:  # 如果 x 超过限制，重置 x 并移动到下一行
        x = 0
        y += step_y

# 2. 处理边：为每个边添加唯一的 ID，添加 'data' 字段并将原来的 'value' 赋值给 data['label']
for edge in data["edges"]:
    edge["id"] = f'{edge["source"]}->{edge["target"]}'
    edge["data"] = {
        "label": edge.pop("value")  # 将 'value' 移到 'data' 的 'label' 字段中
    }

# 将处理后的数据写入输出文件
write_json(output_file, data)

# 输出成功信息
print(f'处理后的 JSON 数据已保存到 {output_file}')
