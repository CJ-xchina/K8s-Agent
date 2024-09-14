import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from bean.graph.GraphManager import GraphManager
from bean.resources.pod import Pod
from executor import PodAgent
from utils.Kubernetes_api import kubectl_get_details

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# 模拟的检查函数
import threading

# 模拟的检查函数
def check_json_format(json_map, event):
    """
    检查 JSON 格式的完整性，如果无法解析则返回错误。
    """
    try:
        # 检查传入的是否为一个字典
        if not isinstance(json_map, dict):
            raise ValueError("Invalid JSON format")
    except Exception as e:
        socketio.emit('check_update', {'task': 'JSON格式检查', 'result': 'failed', 'errorMessage': str(e)})
        event.set()
        return

    socketio.emit('check_update', {'task': 'JSON格式检查', 'result': 'success'})
    event.set()


def check_graph_structure(json_map, event):
    """
    检查图结构：
    1. 每个图应仅有一个 parentNode 为 "" 的 input 类型节点。
    2. 每个 group 类型节点都应该包含且仅包含一个 input 类型节点。
    3. 每个 input 节点必须有且仅有一个连接的出边。
    4. group 节点之间只能连接到其他 group 节点。
    5. group 节点不能作为 default 或 output 节点的目标节点。
    6. default 和 output 节点必须有父节点。
    7. 图中不应有孤立节点，所有节点必须通过边与其他节点连接。
    """
    try:
        flow_data_map = json_map.get('flowDataMap', [])

        for graph in flow_data_map:
            graph_id = graph[0]
            graph_info = graph[1]
            nodes = graph_info['nodes']
            edges = graph_info['edges']

            # 1. 确保每个图有一个 parentNode 为 "" 的 input 节点
            input_nodes = [node for node in nodes if node.get('type') == 'input' and node.get('parentNode') == '']
            if len(input_nodes) != 1:
                socketio.emit('check_update', {
                    'task': '图结构检查',
                    'result': 'failed',
                    'errorMessage': f'图 {graph_id} 应该有且只有一个外层开始节点, 但找到了 {len(input_nodes)} 个！'
                })
                event.set()
                return

            # 2. 确保每个 group 都有且仅有一个 input 节点
            group_nodes = [node for node in nodes if node.get('type') == 'group']
            for group in group_nodes:
                group_id = group.get('id')
                group_input_nodes = [node for node in nodes if node.get('type') == 'input' and node.get('parentNode') == group_id]

                if len(group_input_nodes) != 1:
                    socketio.emit('check_update', {
                        'task': '图结构检查',
                        'result': 'failed',
                        'errorMessage': f'组 {group_id} 中应该有且仅有一个输入节点, 但找到了 {len(group_input_nodes)} 个！'
                    })
                    event.set()
                    return

            # 3. 每个 input 节点必须有且仅有一个连接的出边
            for node in input_nodes:
                node_id = node['id']
                out_edges = [edge for edge in edges if edge['source'] == node_id]
                if len(out_edges) != 1:
                    socketio.emit('check_update', {
                        'task': '图结构检查',
                        'result': 'failed',
                        'errorMessage': f'Input 节点 {node_id} 必须有且仅有一个连接的出边, 但找到了 {len(out_edges)} 个！'
                    })
                    event.set()
                    return

            # 4. group 节点之间只能连接到其他 group 节点
            for group in group_nodes:
                group_id = group['id']
                group_edges = [edge for edge in edges if edge['source'] == group_id]
                for edge in group_edges:
                    target_node = next((node for node in nodes if node['id'] == edge['target']), None)
                    if target_node and target_node.get('type') != 'group':
                        socketio.emit('check_update', {
                            'task': '图结构检查',
                            'result': 'failed',
                            'errorMessage': f'Group 节点 {group_id} 连接到了非 group 节点 {target_node["id"]}'
                        })
                        event.set()
                        return

            # 5. group 节点不能作为 default 或 output 节点的目标节点
            for edge in edges:
                target_node = next((node for node in nodes if node['id'] == edge['target']), None)
                source_node = next((node for node in nodes if node['id'] == edge['source']), None)
                if target_node and target_node.get('type') == 'group':
                    if source_node and source_node.get('type') in ['default', 'output']:
                        socketio.emit('check_update', {
                            'task': '图结构检查',
                            'result': 'failed',
                            'errorMessage': f'Default 或 output 节点 {source_node["id"]} 不能指向 group 节点 {target_node["id"]}'
                        })
                        event.set()
                        return

            # 6. default 和 output 节点必须有父节点
            for node in nodes:
                if node.get('type') in ['default', 'output'] and not node.get('parentNode'):
                    socketio.emit('check_update', {
                        'task': '图结构检查',
                        'result': 'failed',
                        'errorMessage': f'节点 {node["id"]} (类型 {node["type"]}) 没有父节点'
                    })
                    event.set()
                    return

            # 7. 确保没有孤立节点
            connected_node_ids = set([edge['source'] for edge in edges] + [edge['target'] for edge in edges])
            for node in nodes:
                if node['id'] not in connected_node_ids:
                    socketio.emit('check_update', {
                        'task': '图结构检查',
                        'result': 'failed',
                        'errorMessage': f'节点 {node["id"]} 是孤立节点，没有任何连接'
                    })
                    event.set()
                    return

    except Exception as e:
        socketio.emit('check_update', {'task': '图结构检查', 'result': 'failed', 'errorMessage': str(e)})
        event.set()
        return

    socketio.emit('check_update', {'task': '图结构检查', 'result': 'success'})
    event.set()



def check_nodes_connections(json_map, event):
    """
    检查节点连接，特别是 type = default 和 type = group 的节点：
    """
    try:
        flow_data_map = json_map.get('flowDataMap', [])
        tree_data = json_map.get('treeData', [])

        tree_map = {child['id']: tree['label'] for tree in tree_data for child in tree['children']}

        for graph in flow_data_map:
            graph_id = graph[0]
            graph_info = graph[1]

            for node in graph_info.get('nodes', []):
                node_type = node.get('type', '')
                node_id = node.get('id', '')
                category = tree_map.get(graph_id, '未知分类')

                if node_type == 'default':
                    # 检查 action 和 question
                    if not node.get('data', {}).get('action') or not node.get('data', {}).get('question'):
                        socketio.emit('check_update', {
                            'task': '节点连接检查',
                            'result': 'failed',
                            'errorMessage': f'分类 {category} 的流程图 {graph_id} 的节点 {node_id} 的 question 或 action 为空'
                        })
                        event.set()
                        return
                elif node_type == 'group':
                    # 检查 question
                    if not node.get('data', {}).get('question'):
                        socketio.emit('check_update', {
                            'task': '节点连接检查',
                            'result': 'failed',
                            'errorMessage': f'分类 {category} 的流程图 {graph_id} 的推理组节点 {node_id} 的 question 为空'
                        })
                        event.set()
                        return
    except Exception as e:
        socketio.emit('check_update', {'task': '节点连接检查', 'result': 'failed', 'errorMessage': str(e)})
        event.set()
        return

    socketio.emit('check_update', {'task': '节点连接检查', 'result': 'success'})
    event.set()


def check_for_cycles(json_map, event):
    """
    检查图中的循环是否存在。
    使用 DFS 算法进行环的检测。
    """

    def has_cycle(graph_nodes, graph_edges):
        """
        检查单个图是否存在循环。基于 DFS 实现。
        :param graph_nodes: 图中的所有节点
        :param graph_edges: 图中的所有边
        :return: 如果存在环则返回 True，否则返回 False
        """
        # 构建邻接表
        adj_list = {node['id']: [] for node in graph_nodes}
        for edge in graph_edges:
            source = edge['source']
            target = edge['target']
            adj_list[source].append(target)

        visited = set()  # 记录访问过的节点
        stack = set()  # 记录当前递归调用栈中的节点（用于检测回边）

        def dfs(node_id):
            """ 深度优先搜索，检测循环 """
            if node_id in stack:
                return True  # 找到回边，存在循环
            if node_id in visited:
                return False  # 该节点已经被处理过，不存在环

            # 标记当前节点访问
            visited.add(node_id)
            stack.add(node_id)

            # 递归遍历邻接节点
            for neighbor in adj_list[node_id]:
                if dfs(neighbor):
                    return True  # 如果邻接节点中找到环

            # 递归结束，移出当前节点
            stack.remove(node_id)
            return False

        # 对所有未访问的节点进行 DFS 检查
        for node in graph_nodes:
            if node['id'] not in visited:
                if dfs(node['id']):
                    return True  # 找到环

        return False

    try:
        flow_data_map = json_map.get('flowDataMap', [])

        for graph in flow_data_map:
            graph_id = graph[0]
            graph_info = graph[1]

            nodes = graph_info.get('nodes', [])
            edges = graph_info.get('edges', [])

            if has_cycle(nodes, edges):
                socketio.emit('check_update', {
                    'task': '循环检查',
                    'result': 'failed',
                    'errorMessage': f'流程图 {graph_id} 存在循环'
                })
                event.set()
                return  # 立即返回，因为找到了一个有循环的图
    except Exception as e:
        socketio.emit('check_update', {'task': '循环检查', 'result': 'failed', 'errorMessage': str(e)})
        event.set()
        return

    socketio.emit('check_update', {'task': '循环检查', 'result': 'success'})
    event.set()


# 分配并行任务
def perform_checks(json_list):
    """ 对 JSON 列表进行检查 """
    events = [threading.Event() for _ in range(4)]  # 定义四个 Event 对象

    # 创建线程执行四个检查任务
    threading.Thread(target=check_json_format, args=(json_list, events[0])).start()
    threading.Thread(target=check_graph_structure, args=(json_list, events[1])).start()
    threading.Thread(target=check_nodes_connections, args=(json_list, events[2])).start()
    threading.Thread(target=check_for_cycles, args=(json_list, events[3])).start()

    # 等待所有检查任务完成
    for event in events:
        event.wait()

    return True  # 返回 True 表示所有检查任务完成并通过


# 分配并行任务
def perform_checks(json_list):
    """ 对 JSON 列表进行检查 """
    events = [threading.Event() for _ in range(4)]  # 定义四个 Event 对象

    # 创建线程执行四个检查任务
    threading.Thread(target=check_json_format, args=(json_list, events[0])).start()
    threading.Thread(target=check_graph_structure, args=(json_list, events[1])).start()
    threading.Thread(target=check_nodes_connections, args=(json_list, events[2])).start()
    threading.Thread(target=check_for_cycles, args=(json_list, events[3])).start()

    # 等待所有检查任务完成
    for event in events:
        event.wait()

    return True  # 返回 True 表示所有检查任务完成并通过

@app.route('/analyze', methods=['POST'])
def analyze_pod():
    """
    接收 Pod 的 name、namespace 以及多个图的 json 列表，先进行检查，检查通过后构建 GraphManager 并执行 PodAgent 操作。
    """
    try:
        # 从请求中获取 Pod 的 name、namespace 以及多个 json
        data = request.json
        pod_name = data.get('name')
        pod_namespace = data.get('namespace')
        json_list = data.get('json_list')

        # 验证是否传入了必需的字段
        if not pod_name or not pod_namespace or not json_list:
            return jsonify({'error': 'Missing required fields: name, namespace, or json_list'}), 400

        # 构建 Pod 对象
        pod = Pod(name=pod_name, namespace=pod_namespace)

        # 首先对传入的 JSON 数据执行检查
        if not perform_checks(json_list):
            return jsonify({'error': 'JSON data failed the checks'}), 400

        # 检查通过后，使用 json_list 来创建 GraphManager
        graph_manager = GraphManager.from_data(json_list)

        # 构建 PodAgent 并执行
        for graph in graph_manager.graphs.values():
            # 将每个图转换为 JSON 字符串并执行 PodAgent
            agent = PodAgent(json_str=json.dumps(graph.to_json()), pod=pod)
            agent.execute()

        # 返回接受请求的响应，检查进度通过 WebSocket 返回
        return jsonify({'message': 'Pod analysis started, progress will be updated via WebSocket'}), 200

    except Exception as e:
        # 捕获异常并返回 500 错误
        return jsonify({'error': str(e)}), 500




@app.route('/getPodDetails', methods=['GET'])
def get_pod_details():
    """
    获取所有 Pod 的详细信息。

    Returns:
        dict: 所有 Pod 的详细信息。
    """
    try:
        pod_details = kubectl_get_details()  # 调用 kubectl_get_details 函数获取所有 Pod 的信息
        return jsonify(pod_details), 200
    except Exception as e:
        raise e  # 让异常被全局处理器捕获


@socketio.on('connect')
def handle_connect():
    """ WebSocket 客户端连接 """
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """ WebSocket 客户端断开连接 """
    print('Client disconnected')


if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True)
