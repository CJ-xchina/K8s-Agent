import json
import logging
from typing import Optional, Tuple
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from marshmallow import ValidationError
from langchain_core.tools import render_text_description
from langchain.memory import ConversationTokenBufferMemory

from client.baseAgent import BaseAgent
from client.handler import MyPrintHandler
from langchain_core.agents import AgentAction

from client.output_parser import StructuredChatOutputParser
from stage.BaseStage import BaseStage
from typing import List

# 初始化日志记录器
logger = logging.getLogger(__name__)


class PodAgent(BaseAgent):

    def __init__(
            self,
            stages: List[BaseStage],
            max_thought_steps: Optional[int] = 10,  # 最大思考步数，防止死循环
    ):
        if tools is None:
            tools = []

        self.stages = stages
        self.llm = llm  # 设置语言模型
        self.tools = tools  # 初始化工具列表
        self.max_thought_steps = max_thought_steps  # 设置最大思考步数
        self.output_parser = StructuredChatOutputParser()  # 设置输出解析器
        self.prompt = self.__init_prompt(prompt)  # 初始化提示模板
        self.llm_chain = self.prompt | self.llm | StrOutputParser()  # 创建语言模型链
        self.verbose_printer = MyPrintHandler()  # 设置打印处理器
        self.final_prompt = PromptTemplate.from_template(final_prompt) if final_prompt != "" else prompt

    def __init_prompt(self, prompt):
        """
        初始化提示模板，将工具描述和格式说明部分化为模板的一部分。
        """
        return PromptTemplate.from_template(prompt).partial(
            tools=render_text_description(self.tools),  # 渲染工具描述
            format_instructions=self.__chinese_friendly(  # 处理格式说明
                self.output_parser.get_format_instructions(),
            )
        )

    def run(self, task_description: str) -> str:
        """Agent主流程，处理任务描述并返回结果。"""

        thought_step_count = 0  # 初始化思考步数

        # 初始化记忆
        agent_memory = ConversationTokenBufferMemory(
            llm=self.llm,
            max_token_limit=4000,  # 设置记忆中的最大Token数
        )
        agent_memory.save_context(
            {"input": "\ninit"},
            {"output": "\n开始"}
        )

        last_response = ""
        # 开始逐步思考
        while thought_step_count < self.max_thought_steps:
            print(f">>>>Round: {thought_step_count}<<<<")
            action, response = self.__step(
                task_description=task_description,
                memory=agent_memory
            )
            last_response = response

            # 如果是结束指令，执行最后一步
            if action.type == "AgentFinish":
                break

            # 执行动作
            observation = self.__exec_action(action)
            print(f"----\nObservation:\n{observation}")
            # 更新记忆
            self.__update_memory(agent_memory, response, observation)

            thought_step_count += 1

        if thought_step_count >= self.max_thought_steps:
            # 如果思考步数达到上限，返回错误信息
            reply = "抱歉，我没能完成您的任务。"
        else:
            # 否则，执行最后一步
            final_chain = self.final_prompt | self.llm | StrOutputParser()
            reply = final_chain.invoke({
                "task_description": task_description,
                "memory": agent_memory,
                "conclusion": last_response
            })

        return reply

    def __step(self, task_description: str, memory) -> Tuple[AgentAction, str]:
        """执行一步思考，返回动作和响应。"""
        response = ""
        for s in self.llm_chain.stream({
            "task_description": task_description,
            "memory": memory,
        }, config={
            "callbacks": [
                self.verbose_printer
            ]
        }):
            response += s

        action = self.output_parser.parse(response)  # 解析出动作
        return action, response

    def __exec_action(self, action: AgentAction) -> str:
        """根据解析出的动作执行相应的工具。"""
        observation = "没有找到工具"
        for tool in self.tools:
            if tool.name == action.tool:
                print(f"----------------------------------------\n调用工具：{tool.name}")
                try:
                    # 执行工具
                    observation = tool.run(action.tool_input)
                except ValidationError as e:
                    # 工具的入参异常
                    observation = (
                        f"Validation Error in args: {str(e)}, args: {action.tool_input}"
                    )
                except Exception as e:
                    # 工具执行异常
                    observation = f"Error: {str(e)}, {type(e).__name__}, args: {action.tool_input}"

        return observation

    @staticmethod
    def __update_memory(agent_memory, response, observation):
        """更新记忆上下文。"""
        agent_memory.save_context(
            {"input": response},
            {"output": "Observation:" + str(observation)}
        )

    @staticmethod
    def __chinese_friendly(string: str) -> str:
        """处理字符串，使其更加符合中文使用习惯。"""
        lines = string.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('{') and line.endswith('}'):
                try:
                    lines[i] = json.dumps(json.loads(line), ensure_ascii=False)
                except:
                    pass
        return '\n'.join(lines)
