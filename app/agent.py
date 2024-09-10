from flask import Flask, request, jsonify
from executor import Pod, PodAgent
from utils.Kubernetes_api import kubectl_get_details
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 定义标准化的异常处理器



@app.route('/analyze', methods=['POST'])
def analyze_pod():
    """
    接收多个Pod的name、namespace以及单个图的json，构建PodAgent并执行execute操作。
    """
    try:
        # 从请求中获取Pod的name、namespace列表以及json
        data = request.json
        pod_names = data.get('names')
        pod_namespaces = data.get('namespaces')
        json_str = data.get('json')

        # 验证是否传入了必需的字段
        if not pod_names or not pod_namespaces or not json_str:
            return jsonify({'error': 'Missing required fields: names, namespaces, or json'}), 400

        # 检查names和namespaces的长度是否匹配
        if len(pod_names) != len(pod_namespaces):
            return jsonify({'error': 'The length of names and namespaces must be the same'}), 400

        # 对每个Pod进行处理
        for pod_name, pod_namespace in zip(pod_names, pod_namespaces):
            # 构建Pod对象
            pod = Pod(name=pod_name, namespace=pod_namespace)

            # 构建PodAgent对象
            agent = PodAgent(json_str=json_str, pod=pod)

            # 执行PodAgent的逻辑
            agent.execute()

        # 返回成功消息
        return jsonify({'message': 'Pod analysis executed successfully for all Pods'}), 200

    except Exception as e:
        raise e  # 让异常被全局处理器捕获


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
