from typing import Type

from langchain.tools import BaseTool
from bean.graph.llmChatGraph import LlmChatGraph
from pydantic import PrivateAttr, BaseModel, Field


class GraphToolInput(BaseModel):
    condition: str = Field(
        description="需要你在condition中填入你本次的判断结果！")


class GraphTool(BaseTool):
    name = "graph_tool"
    description = """
如果你认为是正确的则填入'true'，你认为错误的则跳入'false',例如输出
'{
"action": "graph_tool",
"action_input": {
"condition": "true"
}
}'
代表你人为本次判断为正确,同样的如果condition："false"，则你认为本次判断的结果应该为错误的或者是没有。

"""
    _graph: LlmChatGraph = PrivateAttr()
    args_schema: Type[BaseModel] = GraphToolInput  # 需要定义输入的结构

    class Config:
        underscore_attrs_are_private = True  # 允许使用下划线开头的私有属性

    def __init__(self, graph: LlmChatGraph):
        super().__init__()
        self._graph = graph

    def _run(self, condition: str) -> str:
        try:
            return self._graph.get_node_details_by_condition(condition)
        except Exception as e:
            return f"发生错误: {e}"

    def _arun(self, node_id: str, condition: str):
        raise NotImplementedError("该工具不支持异步执行")

