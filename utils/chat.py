from typing import List, Union
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import PromptTemplate

def chat_with_model_template(model: BaseChatModel, prompt_template: PromptTemplate, variables: dict, return_str: bool = False) -> Union[str, List[Union[str, dict]], BaseMessage]:
    """
    调用一次语言模型并生成响应。

    参数:
        model (BaseChatModel): 语言模型实例，用于生成对话响应。
        prompt (PromptTemplate): 经过格式化的对话提示模板。
        variables (dict): 注入到 PromptTemplate 中的参数字典。
        return_str (bool): 是否返回字符串形式的响应。默认为 False，如果为 True，则返回字符串。

    返回:
        BaseMessage 或 str: 语言模型生成的对话响应。如果 return_str 为 True，则返回字符串，否则返回 BaseMessage。

    抛出:
        ValueError: 如果生成的响应为空。
    """
    formatted_prompt = prompt_template.format_prompt(**variables)
    print(f"Formatted prompt: {formatted_prompt}")

    response = model.invoke(formatted_prompt)

    if not response:
        raise ValueError("生成的响应为空，可能是 chat_model 生成过程中出现问题。")

    # 如果 return_str 为 True，提取内容并返回字符串
    if return_str:
        if isinstance(response, AIMessage):
            return response.content
        return str(response)

    # 否则返回 BaseMessage 对象
    return response


def chat_with_model_str(model: BaseChatModel, prompt: str, return_str: bool = False) -> Union[str, List[Union[str, dict]], BaseMessage]:
    """
    调用一次语言模型并生成响应。

    参数:
        model (BaseChatModel): 语言模型实例，用于生成对话响应。
        prompt (str): 经过格式化的对话字符提示词。
        return_str (bool): 是否返回字符串形式的响应。默认为 False，如果为 True，则返回字符串。

    返回:
        BaseMessage 或 str: 语言模型生成的对话响应。如果 return_str 为 True，则返回字符串，否则返回 BaseMessage。

    抛出:
        ValueError: 如果生成的响应为空。
    """
    print(f"Prompt: {prompt}")

    response = model.invoke(prompt)

    if not response:
        raise ValueError("生成的响应为空，可能是 chat_model 生成过程中出现问题。")

    # 如果 return_str 为 True，提取内容并返回字符串
    if return_str:
        if isinstance(response, AIMessage):
            return response.content
        return str(response)

    # 否则返回 BaseMessage 对象
    return response
