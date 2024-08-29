from kubernetes import client, config

config.load_kube_config()


def kubernetes_client():
    """Returns an instance of CoreV1Api to interact with Kubernetes cluster."""
    return client.CoreV1Api()