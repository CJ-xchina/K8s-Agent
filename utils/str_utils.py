import re


async def process_regex(result: str, regex: str) -> str:
    """
    使用正则表达式处理结果，并返回匹配的结论。

    Args:
        result (str): 动作执行的结果。
        regex (str): 用于匹配的正则表达式。

    Returns:
        str: 正则匹配到的结论，或者返回匹配失败信息。
    """
    match = re.search(regex, result)
    if match:
        return match.group(0)
    else:
        return f"正则表达式匹配失败: '{result}' 配置的正则: {regex}"