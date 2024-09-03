from langchain.agents import AgentExecutor
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI
from k8s_tools import kubectl_describe, kubectl_pod_logs, kubectl_get_pods
from langgraph.checkpoint.memory import MemorySaver  # an in-memory checkpointer
from utils.prompt_utils import get_prompt
from client.base import create_structured_chat_agent
from utils.tools import render_text_description_and_args

# 初始化模型和会话历史
model = ChatOpenAI(model="qwen2:7b-instruct-fp16 ", base_url="http://localhost:11434/v1", api_key="123")
memory = InMemoryChatMessageHistory(session_id="test-session")

# 定义提示模板
# query2 = """
# In the default namespace, please first check the names of all the pods. Find the name of the pod that ends with "k26cn", and return the log content of this pod to me!
# """
#
query3 = ("请你根据我提供给你的工具，使用日志、describe描述以及多维角度，判断在default命名中间中的名称为'k8s-test-3'的pod是否正常运行！是否存在故障问题！请你详细查找并且认真分析总结，中文回复！如果出现问题"
          "我希望你能够找到并且详细分析问题从产生的原因并且告诉我解决方法！问题没有被详细分析并输出前，不允许输出Final Answer的动作！")
memory = MemorySaver()
# 定义工具
tools = [kubectl_describe, kubectl_pod_logs, kubectl_get_pods]

config = {"configurable": {"session_id": "test-session"}}

# PROMPT = hub.pull("hwchase17/structured-chat-agent", api_key='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')
PROMPT = get_prompt()

agent = create_structured_chat_agent(model, tools, prompt=PROMPT, tools_renderer=render_text_description_and_args)
agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=False,
                                                    handle_parsing_errors=True)
for step in agent_executor.stream({"input": f"{query3}"}):
    print(step)
# print(agent_executor.invoke({"input": f"{query}"}))
