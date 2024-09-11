class Pod:
    def __init__(self, name: str, namespace: str):
        """
        初始化Pod对象，并传入基础信息。

        参数:
            name (str): Pod的名称。
            namespace (str): Pod所在的命名空间。
        """
        self.name = name
        self.namespace = namespace

    def get_info(self) -> dict:
        """
        返回Pod基础信息的字典。

        返回:
            dict: 包含Pod基础信息的字典。
        """
        return {
            "resource_type": "Kubernetes Pod",
            "name": self.name,
            "namespace": self.namespace
        }