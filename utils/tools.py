from langchain.agents import AgentOutputParser
from langchain_core.tools.base import BaseTool
from langchain_core.agents import AgentAction, AgentFinish

from marshmallow import ValidationError





def extract_tool_signature(output: str, tool_parser: AgentOutputParser):
    """
    从模型生成的输出中提取工具的名称和参数签名，用于一致性检查。

    参数:
        output (str): 模型生成的输出字符串。
        tool_parser (AgentOutputParser): 用于解析输出的解析器。

    返回:
        tuple: 包含工具名称和参数的元组。如果输出无法解析，则返回原始输出字符串。
    """
    parsed_output = tool_parser.parse(output)

    if isinstance(parsed_output, (AgentAction, AgentFinish)):
        # 将工具输入的键和值都转换为小写
        lowercase_tool_input = {
            k.lower(): v.lower() if isinstance(v, str) else v
            for k, v in parsed_output.tool_input.items()
        }
        return parsed_output.tool, frozenset(lowercase_tool_input.items())
    return output


def execute_action(tools: BaseTool, action: AgentAction) -> str:
    """
    根据解析出的动作执行相应的工具。

    参数:
        tools (list[BaseTool]): 工具列表，每个工具都具有 `name` 和 `run` 方法。
        action (AgentAction): 解析出的动作对象，包含工具名称和工具输入参数。

    返回:
        str: 工具执行的结果或异常信息。
    """
    observation = ""  # 用于存储工具执行后的观察结果

    for tool in tools:
        if tool.name == action.tool:
            try:
                # 调用对应工具的 `run` 方法，执行工具操作
                observation = tool.run(action.tool_input)
                break
            except Exception as e:
                # 处理工具执行过程中的其它异常
                observation = (f"执行工具时产生了异常，因为你传入了名称错误的参数, 程序报错信息如下: {str(e)}."
                               f"--------------------"
                               f"本次传入的参数为: {action.tool_input}, 这是个错误名称的参数!!你应该传入的参数为: {tool.args}")
                raise ValidationError(observation)

    if observation == "":
        available_tools = [tool.name for tool in tools]
        observation = f"工具的名称错误, 没有找到名为 '{action.tool}' 的工具。可用的工具包括: {', '.join(available_tools)}。请你注意是否是拼写错误或者是大小写错误！"
        raise ValidationError(observation)

    return observation
