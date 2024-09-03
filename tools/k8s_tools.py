import subprocess
import yaml
from langchain.tools import tool
from setting.k8s import kubernetes_client

@tool(parse_docstring=True)
def kubectl_describe(resource_type: str, resource_name: str, namespace: str = "default") -> str:
    """
    执行 `kubectl describe` 命令并返回过滤后的纯文本格式结果。

    Args:
        resource_type : Kubernetes资源类型 (例如: pod, service)。
        resource_name : 资源名称。
        namespace : 资源所在的命名空间，默认是 "default"。

    Returns:
        str: 指定资源的详细描述，格式为纯文本，已过滤无关数据。
    """

    v1 = kubernetes_client()

    if resource_type.lower() == "pod":
        resource = v1.read_namespaced_pod(name=resource_name, namespace=namespace)
    elif resource_type.lower() == "service":
        resource = v1.read_namespaced_service(name=resource_name, namespace=namespace)
    # 可根据需要添加更多的资源类型。
    else:
        return f"资源类型 {resource_type} 不受支持。"

    resource_dict = resource.to_dict()

    result = []
    result.append(f"资源: {resource_dict.get('kind')} - {resource_dict['metadata'].get('name')}")
    result.append(f"命名空间: {resource_dict['metadata'].get('namespace')}")
    result.append(f"标签: {resource_dict['metadata'].get('labels')}")
    result.append(f"UID: {resource_dict['metadata'].get('uid')}")

    result.append("\nPod 规格:")
    result.append(f"节点名称: {resource_dict['spec'].get('node_name')}")
    result.append(f"容器:")
    for container in resource_dict['spec'].get('containers', []):
        result.append(f"  - 名称: {container.get('name')}")
        result.append(f"    镜像: {container.get('image')}")
        result.append(f"    资源: {container.get('resources')}")
        result.append(f"    卷挂载: {container.get('volume_mounts')}")

    result.append("\nPod 状态:")
    result.append(f"阶段: {resource_dict['status'].get('phase')}")
    result.append(f"条件:")
    for condition in resource_dict['status'].get('conditions', []):
        result.append(f"  - 类型: {condition.get('type')}, 状态: {condition.get('status')}, 最后转换时间: {condition.get('last_transition_time')}")

    result.append(f"容器状态:")
    for cstatus in resource_dict['status'].get('container_statuses', []):
        result.append(f"  - 名称: {cstatus.get('name')}, 状态: {cstatus.get('state')}, 就绪: {cstatus.get('ready')}")

    return "\n".join(result)


@tool(parse_docstring=True)
def kubectl_pod_logs(pod_name: str, namespace: str = "default", container_name: str = None) -> str:
    """
    获取指定 Pod 的日志。

    Args:
        pod_name : Pod 的名称。
        namespace : Pod 所在的命名空间，默认是 "default"。
        container_name : 指定容器的名称，如果 Pod 中有多个容器。

    Returns:
        str: 指定 Pod（及容器）的日志。
    """
    v1 = kubernetes_client()
    logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, container=container_name)

    return logs


@tool(parse_docstring=True)
def kubectl_get_details(namespace: str, pod_name: str) -> str:
    """
    获取指定命名空间和指定名称的 Pod 详细信息。

    Args:
        namespace : Pod 所在的命名空间。
        pod_name : Pod 的名称。

    Returns:
        dict: Pod 的详细信息，以字典形式返回。
    """
    v1 = kubernetes_client()
    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    # 将 Pod 对象转换为字典
    pod_details = pod.to_dict()

    return pod_details