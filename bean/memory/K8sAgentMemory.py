import json
from enum import Enum
from typing import Any, Callable, Dict, List

from bean.memory.baseMemory import MemoryBase


# 定义存储键名的枚举类
class MemoryKey(Enum):
    EXPERT_QUESTION = "expert_question"


# 内存记忆类
class K8sAgentMemory(MemoryBase):
    def __init__(self):
        super().__init__()
