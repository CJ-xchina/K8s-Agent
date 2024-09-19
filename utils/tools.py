from typing import List, Callable, Union

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.tools import BaseTool
from marshmallow import ValidationError

from bean.resources.pod import Pod
from tools.k8s_tools import kubectl_describe, kubectl_pod_logs, kubectl_get_details, kubectl_command


def get_all_tools() -> list[
    Callable[[str, str], str] | Callable[[str, str], str] | Callable[[str, str], str] | Callable[[str], str]]:
    return [kubectl_describe, kubectl_pod_logs, kubectl_get_details, kubectl_command]


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
        if isinstance(parsed_output.tool_input, str):
            return parsed_output.tool, parsed_output.tool_input.lower()

        lowercase_tool_input = {
            k.lower(): v.lower() if isinstance(v, str) else v
            for k, v in parsed_output.tool_input.items()
        }
        return parsed_output.tool, frozenset(lowercase_tool_input.items())
    return output


def execute_action(action: Union[str, AgentAction], tools: List[BaseTool] = None) -> str:
    """
    根据解析出的动作执行相应的工具。如果没有匹配的工具, 默认执行Kubectl命令行工具

    参数:
        tools (list[BaseTool]): 工具列表，每个工具都具有 `name` 和 `run` 方法。
        action (AgentAction): 解析出的动作对象，包含工具名称和工具输入参数。

    返回:
        str: 工具执行的结果或异常信息。
    """
    if tools is None:
        tools = get_all_tools()

    # 如果action为字符串, 默认调用`kubectl_command` 执行这条kubectl指令
    if isinstance(action, str):
        action = AgentAction(tool="kubectl_command", tool_input=action, log="")
    observation = ""  # 用于存储工具执行后的观察结果

    run_any_tools = False

    for tool in tools:
        if tool.name == action.tool:
            try:
                print(f"执行工具：{tool.name}\n "
                      f"传入参数: {action.tool_input}")
                observation = tool.run(action.tool_input)
                run_any_tools = True
                print(f"执行结果: {observation}\n\n\n")
                break
            except Exception as e:
                # 处理工具执行过程中的其它异常
                observation = (f"执行工具时产生了异常，因为你传入了名称错误的参数, 程序报错信息如下: {str(e)}."
                               f"--------------------"
                               f"本次传入的参数为: {action.tool_input}, 这是个错误名称的参数!!你应该传入的参数为: {tool.args}")
                raise ValidationError(observation)

    if run_any_tools is not True:
        available_tools = [tool.name for tool in tools]
        observation = f"工具的名称错误, 没有找到名为 '{action.tool}' 的工具。可用的工具包括: {', '.join(available_tools)}。请你注意是否是拼写错误或者是大小写错误！"
        raise ValidationError(observation)

    return observation


def validate_tool_input(action: AgentAction, tools: List[BaseTool] = None) -> None:
    """
    验证 action 中的输入参数是否符合工具的要求。

    参数:
        tools (List[BaseTool]): 工具实例数组。
        action (AgentAction): 包含工具名称和输入参数的动作对象。

    抛出:
        ValidationError: 如果输入参数与工具的要求不匹配，则抛出异常。
    """
    if tools is None:
        tools = get_all_tools()
    # 遍历工具列表，找到与 action.tool 匹配的工具
    for tool in tools:
        if tool.name == action.tool:
            required_args = set(tool.args.keys())
            provided_args = set(action.tool_input.keys())

            # 检查是否有缺失的参数
            missing_args = required_args - provided_args
            if missing_args:
                raise ValidationError(
                    f"工具 '{tool.name}' 缺少必需的参数: {', '.join(missing_args)}。"
                    f"提供的参数为: {provided_args}。必需的参数为: {required_args}。"
                )

            # 检查是否有多余的参数
            extra_args = provided_args - required_args
            if extra_args:
                raise ValidationError(
                    f"工具 '{tool.name}' 收到了多余的参数: {', '.join(extra_args)}。"
                    f"提供的参数为: {provided_args}。必需的参数为: {required_args}。"
                )

            # 如果工具匹配且参数验证成功，则退出函数
            return

    # 如果没有找到匹配的工具，抛出异常
    raise ValidationError(f"未找到与工具名称 '{action.tool}' 匹配的工具。")
