from typing import List

from langchain_core.agents import AgentAction

from stage.BaseStage import BaseStage, StageType


class BaseAgent:
    """
    BaseAgent 基类，抽象了一个智能代理的基础功能。

    Attributes:
        stages (List[Stage]): 存储多个Stage对象的数组。
        max_thought_steps (int): 最大思考步数，防止死循环。

    Methods:
        run(task_description: str) -> str: 运行Agent主流程的方法。
        __exec_action(action: AgentAction) -> str: 执行动作的方法。
        __update_memory(agent_memory, response, observation): 更新记忆的方法。
    """

    def __init__(self, stages: List[BaseStage], max_thought_steps: int = 10):
        """
        初始化BaseAgent类。

        Args:
            stages (List[Stage]): 传入的Stage数组。
            max_thought_steps (int): 最大思考步数，默认值为10。
            current_stage (StageType): 存储当前阶段的状态，初始为StageType.START。

        """
        self.stages = stages
        self.max_thought_steps = max_thought_steps
        self.current_stage = StageType.START

    def run(self, task_description: str) -> str:
        """
        运行Agent主流程的方法，处理任务描述并返回结果。

        Args:
            task_description (str): 描述任务的字符串。

        Returns:
            str: 处理结果的字符串。
        """
        pass

    def __exec_action(self, action: AgentAction) -> str:
        """
        根据解析出的动作执行相应的工具。

        Args:
            action (AgentAction): 包含动作和工具信息的AgentAction对象。

        Returns:
            str: 执行动作后的观察结果。
        """
        pass

    def __update_memory(self, agent_memory, response, observation):
        """
        更新Agent的记忆。

        Args:
            agent_memory: 存储Agent记忆的对象。
            response (str): 生成的响应。
            observation (str): 动作执行后的观察结果。
        """
        pass
