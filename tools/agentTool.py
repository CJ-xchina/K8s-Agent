from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from bean.agent.baseAgent import baseAgent
from bean.stage.ToolStage import ToolStage


class AgentToolInput(BaseModel):
    input: str = Field(
        description="需要你在condition中填入你本次的判断结果！")


class agentTool(BaseTool):
    name: str = PrivateAttr()
    description: str = PrivateAttr()
    args_schema: Type[BaseModel] = AgentToolInput  # 需要定义输入的结构

    _stage: ToolStage = PrivateAttr()
    _agent: baseAgent = PrivateAttr()

    class Config:
        underscore_attrs_are_private = True  # 允许使用下划线开头的私有属性

    def __init__(self, stage: ToolStage, agent: baseAgent):
        super().__init__()
        self.name = stage.get_name()
        self.description = stage.get_description()
        self._stage = stage
        self._agent = agent

    def _run(self, input: str) -> str:
        """
        运行该工具，调用对应 ToolStage 的 _step 方法。

        参数:
            description (str): 传递给 _step 方法的输入数据。

        返回:
            str: _step 方法的执行结果。
        """
        return self._stage._step({"input": input})


def generate_agent_tools(agent: baseAgent) -> List[BaseTool]:
    """
    为每个 ToolStage 生成一个工具，并返回这些工具的列表。

    参数:
        agent (baseAgent): 包含多个 ToolStage 的 Agent 实例。

    返回:
        List[BaseTool]: 封装为数组的多个工具实例。
    """
    tools = []
    for stage in agent.tool_stages:
        tool = agentTool(stage=stage, agent=agent)
        tools.append(tool)
    return tools
