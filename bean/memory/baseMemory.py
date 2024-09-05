import json
from enum import Enum
from typing import Any, Callable, Dict, List


# 内存记忆基础类
class MemoryBase:
    def __init__(self):
        # 使用字典来存储键值对，值为列表以支持多次存储同一键
        self.memory_store: Dict[Enum, List[Any]] = {}

        # 钩子函数列表，输入输出前后可以执行的外部函数
        self.hooks_before_store: List[Callable[[Enum, Any], None]] = []
        self.hooks_after_store: List[Callable[[Enum, Any], None]] = []
        self.hooks_before_get: List[Callable[[List[Enum]], None]] = []
        self.hooks_after_get: List[Callable[[Dict[Enum, List[Any]]], None]] = []

    # 添加钩子函数
    def add_hook(self, when: str, hook: Callable):
        if when == "before_store":
            self.hooks_before_store.append(hook)
        elif when == "after_store":
            self.hooks_after_store.append(hook)
        elif when == "before_get":
            self.hooks_before_get.append(hook)
        elif when == "after_get":
            self.hooks_after_get.append(hook)
        else:
            raise ValueError(f"Invalid hook timing: {when}")

    # 存储数据，使用指定的枚举键
    def store_data(self, key: Enum, data: Any):
        """
        存储数据到指定的键名下，同时调用钩子函数。
        """
        # 在存储前调用钩子
        for hook in self.hooks_before_store:
            hook(key, data)

        if key not in self.memory_store:
            self.memory_store[key] = []
        self.memory_store[key].append(data)

        # 在存储后调用钩子
        for hook in self.hooks_after_store:
            hook(key, data)

    # 读取数据，并返回JSON格式字符串
    def get_data(self, keys: List[Enum]) -> str:
        """
        获取指定键名的存储数据，同时调用钩子函数，返回JSON格式字符串。
        """
        # 在获取前调用钩子
        for hook in self.hooks_before_get:
            hook(keys)

        result = {}
        for key in keys:
            result[key] = self.memory_store.get(key, [])

        # 在获取后调用钩子
        for hook in self.hooks_after_get:
            hook(result)

        # 将字典中的 Enum 键转换为字符串，再转换为 JSON 格式字符串
        result_str_keys = {key.value: value for key, value in result.items()}

        return json.dumps(result_str_keys)

