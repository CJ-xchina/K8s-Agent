from client.PodAgent import K8s_Agent
from setting.prompt_Action import prompt_text, final_prompt
from client.k8s_tools import kubectl_describe, kubectl_pod_logs

import logging


def setup_logging():
    # 创建日志记录器
    logger = logging.getLogger()

    # 设置日志级别为INFO
    logger.setLevel(logging.INFO)

    # 创建一个控制台处理器并设置日志级别为INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建一个简单的日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # 将处理器添加到日志记录器中
    logger.addHandler(console_handler)


if __name__ == "__main__":
    setup_logging()

    tools = [kubectl_pod_logs, kubectl_describe]

    my_agent = K8s_Agent(
        tools=tools,
        prompt=prompt_text,
        final_prompt=final_prompt,
    )

    task = """请你根据我提供给你的工具，使用日志、describe描述以及多维角度，判断在default命名中间中的名称为'k8s-test-1-64ddfdff5d-6t7m6'的pod是否正常运行！是否存在故障问题！请你详细查找并且认真分析总结，中文回复！如果出现问题"
          "我希望你能够找到并且详细分析问题从产生的原因并且告诉我解决方法！问题没有被详细分析并输出前，不允许输出Final Answer的动作！"""
    reply = my_agent.run(task)
    print(reply)
