import subprocess

import yaml
from langchain.tools import tool
from setting.k8s import kubernetes_client

#
@tool(parse_docstring=True)
def kubectl_describe(resource_type: str, resource_name: str, namespace: str = "default") -> str:
    """
    Executes the `kubectl describe` command and returns the filtered result in plain text format.

    Args:
        resource_type: The type of Kubernetes resource (e.g., pod, service).
        resource_name: The name of the resource.
        namespace: The namespace of the resource, default is "default".

    Returns:
        The detailed description of the specified resource in plain text format, with irrelevant data filtered out.
    """
    v1 = kubernetes_client()

    if resource_type == "pod" or resource_type == "Pod":
        resource = v1.read_namespaced_pod(name=resource_name, namespace=namespace)
    elif resource_type == "service" or resource_type == "Service":
        resource = v1.read_namespaced_service(name=resource_name, namespace=namespace)
    # Add more elif branches for other resource types as needed.
    else:
        return f"Resource type {resource_type} not supported."

    # Convert the resource object to a dictionary
    resource_dict = resource.to_dict()

    # Prepare the plain text output
    result = []
    result.append(f"Resource: {resource_dict.get('kind')} - {resource_dict['metadata'].get('name')}")
    result.append(f"Namespace: {resource_dict['metadata'].get('namespace')}")
    result.append(f"Labels: {resource_dict['metadata'].get('labels')}")
    result.append(f"UID: {resource_dict['metadata'].get('uid')}")
    # result.append(
    #     f"Owner References: {', '.join([owner.get('name') for owner in resource_dict['metadata'].get('owner_references', [])])}")

    # Spec details
    result.append("\nPod Specification:")
    result.append(f"Node Name: {resource_dict['spec'].get('node_name')}")
    result.append(f"Containers:")
    for container in resource_dict['spec'].get('containers', []):
        result.append(f"  - Name: {container.get('name')}")
        result.append(f"    Image: {container.get('image')}")
        result.append(f"    Resources: {container.get('resources')}")
        result.append(f"    Volume Mounts: {container.get('volume_mounts')}")

    # Status details
    result.append("\nPod Status:")
    result.append(f"Phase: {resource_dict['status'].get('phase')}")
    result.append(f"Conditions:")
    for condition in resource_dict['status'].get('conditions', []):
        result.append(
            f"  - Type: {condition.get('type')}, Status: {condition.get('status')}, Last Transition: {condition.get('last_transition_time')}")

    result.append(f"Container Statuses:")
    for cstatus in resource_dict['status'].get('container_statuses', []):
        result.append(f"  - Name: {cstatus.get('name')}, State: {cstatus.get('state')}, Ready: {cstatus.get('ready')}")

    # Join all the pieces into a single string
    return "\n".join(result)


@tool(parse_docstring=True)
def kubectl_pod_logs(pod_name: str, namespace: str = "default") -> str:
    """
    Retrieves the logs of a specified Pod.

    Args:
        pod_name: The name of the Pod.
        namespace: The namespace of the Pod, default is "default".

    Returns:
        The logs from the specified Pod (and container, if specified).
    """
    v1 = kubernetes_client()
    logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)

    return logs


@tool(parse_docstring=True)
def kubectl_get_pods(namespace: str = "default") -> str:
    """
    Retrieves all Pods in the specified namespace.

    Args:
        namespace: The namespace to list the Pods from, default is "default".

    Returns:
        A list of all Pods in the specified namespace.
    """
    v1 = kubernetes_client()
    pods = v1.list_namespaced_pod(namespace=namespace)
    pod_list = [pod.metadata.name for pod in pods.items]

    return "\n".join(pod_list)


@tool(parse_docstring=True)
def kubectl_command(command: str) -> str:
    """
    该函数传入的字符串是一条完整且最简单的Kubectl指令 ! 不允许使用 -o 让指令输出为 JSON 格式！
    示例：获取指定命名空间 (default) 下的所有 Pods 列表，包含 Pod 的名称、状态、重启次数和运行时长等信息。
    ```json
    {
        "action": "kubectl_command"
        "action_input": "kubectl get pods -n default",
    }
    ```

    Args:
        command: 完整的 `kubectl` 命令字符串，只允许 `kubectl get` 、 `kubectl describe` 和 `kubectl logs`命令。

    Returns:
        命令的执行结果作为字符串返回。
    """
    # 限制只能执行 `kubectl get` 和 `kubectl describe` 命令
    if not (command.startswith("kubectl get") or command.startswith("kubectl describe")) or command.startswith("kubectl logs"):
        raise ValueError("只允许执行 `kubectl get` 或 `kubectl describe` 命令。")

    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return f"命令执行失败: {e.output.decode('utf-8')}"


