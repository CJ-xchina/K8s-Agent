import asyncio

import yaml
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI

from bean.agent.baseAgent import baseAgent
from bean.graph.llmChatGraph import LlmChatGraph
from bean.parser.StructuredChatOutputParser import StructuredChatOutputParser
from bean.parser.StructuredThinkingOutputParser import StructuredThinkingOutputParser
from bean.stage.ThinkingStage import ThinkingStage
from bean.stage.ToolStage import ToolStage
from tools.agentTool import generate_agent_tools
from tools.graphTool import GraphTool
from tools.k8s_tools import kubectl_describe, kubectl_pod_logs, kubectl_get_details
from setting.prompt_Thinking import *
from setting.prompt_Action import *

class Pod:
    def __init__(self, name: str, namespace: str):
        """
        初始化Pod对象，并传入基础信息。

        参数:
            name (str): Pod的名称。
            namespace (str): Pod所在的命名空间。
        """
        self.name = name
        self.namespace = namespace

    def get_info(self) -> str:
        """
        返回Pod基础信息的拼接字符串。

        返回:
            str: 拼接后的Pod基础信息字符串。
        """
        return (f"资源类型 : Kubernetes Pod\n"
                f"Pod Name: {self.name}\n"
                f"Namespace: {self.namespace}\n")


class PodAgent(baseAgent):
    def __init__(self, path: str = "", config_file: str = "", pod: Pod = None):
        self.memory_tool = None
        self.memory_thinking = None
        self.graph = LlmChatGraph("1", path)
        self.config_file = config_file
        self.pod = pod  # 传入的Pod对象
        super().__init__()

    def load_config(self):
        with open(self.config_file, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config

    def replace_details(self, template_str: str) -> str:
        """
        将模板字符串中的{details}替换为Pod的基础信息。

        参数:
            template_str (str): 包含{details}的模板字符串。

        返回:
            str: 替换后的字符串。
        """
        return template_str.replace("{details}", self.pod.get_info())

    def create_tool_stage(self, stage_config, tool_map):
        tools = [tool_map[tool_name] for tool_name in stage_config['tools']]
        memory = self.memory_thinking
        prompt = self.replace_details(globals()[stage_config['prompt']])  # 替换details

        name = stage_config.get('name')
        if name == "process_planning_expert":
            stage = ToolStage(
                prompt=prompt,
                chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16", base_url="http://localhost:11434/v1",
                                      api_key="<KEY>"),
                tool_parser=StructuredChatOutputParser(),
                tools=tools,
                self_consistency_times=stage_config.get('self_consistency_times', 10),
                enable_fixing=stage_config.get('enable_fixing', False),
                fixing_num=stage_config.get('fixing_num', 1),
                name=stage_config.get('name', ""),
                description=stage_config.get('description', ""),
                enable_conclusion=stage_config.get('enable_conclusion', False),
                node_details_func=self.graph.get_current_node_details
            )
        else:
            stage = ToolStage(
                prompt=prompt,
                chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16", base_url="http://localhost:11434/v1",
                                      api_key="<KEY>"),
                tool_parser=StructuredChatOutputParser(),
                tools=tools,
                self_consistency_times=stage_config.get('self_consistency_times', 10),
                enable_fixing=stage_config.get('enable_fixing', False),
                fixing_num=stage_config.get('fixing_num', 1),
                memory=memory,
                name=stage_config.get('name', ""),
                description=stage_config.get('description', ""),
                enable_conclusion=stage_config.get('enable_conclusion', False),
                node_details_func=self.graph.get_current_node_details
            )
        self.tool_stages.append(stage)
        return stage

    def create_thinking_stage(self, stage_config, tool_map):
        tools = tool_map["AgentTool"]
        memory = self.memory_thinking
        prompt = self.replace_details(globals()[stage_config['prompt']])  # 替换details

        stage = ThinkingStage(
            # qwen2:7b-instruct-fp16-instruct-fp16
            chat_model=ChatOpenAI(model="qwen2:7b-instruct-fp16", base_url="http://localhost:11434/v1",
                                  api_key="<KEY>"),
            fixing_model=ChatOpenAI(model="qwen2:7b-instruct-fp16", base_url="http://localhost:11434/v1",
                                    api_key="<KEY>"),
            prompt=prompt,
            tool_parser=StructuredThinkingOutputParser(tools=tools),
            tools=tools,
            self_consistency_times=stage_config.get('self_consistency_times', 10),
            enable_fixing=stage_config.get('enable_fixing', False),

            fixing_num=stage_config.get('fixing_num', 1),
            memory=memory,
        )

        self.thinking_stages.append(stage)
        return stage

    def initialize_stages(self):
        config = self.load_config()
        self.memory_thinking = ConversationBufferMemory()

        tool_map = {
            'GraphTool': GraphTool(graph=self.graph),
            'kubectl_describe': kubectl_describe,
            'kubectl_pod_logs': kubectl_pod_logs,
            'kubectl_get_pods': kubectl_get_details
        }

        # 先初始化 ToolStage
        for stage_config in config['stages']:
            if stage_config['stage_type'] == 'ToolStage':
                self.stages.append(self.create_tool_stage(stage_config, tool_map))

        # 然后生成 AgentTool 并初始化 ThinkingStage
        tool_map['AgentTool'] = generate_agent_tools(self)

        for stage_config in config['stages']:
            if stage_config['stage_type'] == 'ThinkingStage':
                self.stages.append(self.create_thinking_stage(stage_config, tool_map))

    def get_thinking_input(self) -> dict:
        return {"question": self.graph.get_current_node_details()}

    def get_action_input(self, input) -> dict:
        return {"Though": input}

    def get_graph_input(self, input) -> dict:
        return {"llm_input": input}

    def execute(self) -> str:
        while True:
            for cur_stage in self.thinking_stages:
                output = cur_stage._step(self.get_thinking_input())
                print("")


def main():
    pod = Pod(name="crash-loop", namespace="k8sgpt-test")
    pod_agent = PodAgent(path="../../resources/pod_graph.json", config_file="../../resources/pod.yaml", pod=pod)
    pod_agent.execute()


if __name__ == "__main__":
    main()
