from setting.k8s import kubernetes_client


def kubectl_get_details() -> list:
    """
    获取所有命名空间中每个 Pod 的详细信息，仅返回 Pod 的名称、命名空间和运行状态。

    Returns:
        list: 包含每个 Pod 的名称、命名空间和运行状态的字典列表。
    """
    v1 = kubernetes_client()
    pods = v1.list_pod_for_all_namespaces()

    pod_list = []
    for pod in pods.items:
        # 获取 Pod 的状态、名称和命名空间
        status = pod.status.phase
        name = pod.metadata.name
        namespace = pod.metadata.namespace

        # 构建字典并添加到列表中
        pod_list.append({
            'name': name,
            'namespace': namespace,
            'status': status
        })

    return pod_list
