import json
from abc import ABC, abstractmethod
from typing import List, Any


class baseAgent(ABC):
    def __init__(self):
        self.thinking_stages = []
        self.tool_stages = []
        self.stages = []
        self.initialize_stages()

    @abstractmethod
    def initialize_stages(self):
        """
        初始化各个阶段的逻辑，需要在子类中实现。
        """
        pass

    @abstractmethod
    def execute(self):
        pass

    def get_stage_names_str(self) -> str:
        """
        获取所有阶段的名称，返回一个拼接的字符串。

        Returns:
            str: 包含所有阶段名称的字符串，以 ", " 分隔。
        """
        return ", ".join([stage.get_name() for stage in self.tool_stages])

    def get_stage_names(self) -> list[Any]:
        """
        获取所有阶段的名称，返回一个拼接的字符串。

        Returns:
            list: 包含所有阶段名称的数组。
        """
        return [stage.get_name() for stage in self.tool_stages]

    def get_stage_by_name(self, stage_name: str) -> Any:
        for stage in self.stages:
            if stage.get_name() == stage_name:
                return stage

        raise KeyError(f'No such stage: {stage_name}')


    def get_stage_info_json(self) -> str:
        """
        以 JSON 格式返回所有阶段的名称和描述。

        Returns:
            str: JSON 字符串，其中包含每个阶段的名称和对应的描述。
        """
        # 构建一个 name -> description 形式的字典
        result = {stage.get_name(): stage.get_description() for stage in self.tool_stages}

        # 返回 JSON 字符串
        return json.dumps(result, ensure_ascii=False, indent=4)
