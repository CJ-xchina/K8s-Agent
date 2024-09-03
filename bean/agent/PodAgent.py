from langchain.memory import ConversationBufferMemory

from bean.graph.llmChatGraph import LlmChatGraph


class Pod:
    def __init__(self, path: str = ""):
        # 记录Pod分析流程图中的信息
        self.graph = LlmChatGraph(path)

        # 记录Thinking LLM的分析流程
        self.memory_thinking = ConversationBufferMemory()

        # 记录工具调用结果
        self.memory_tool = ConversationBufferMemory()

    def get_thinking_llm_input(self) -> dict:
        """
        获取传入 Thinking LLM 的字典。

        返回:
            dict: 包含 Thinking LLM 需要的输入数据。
        """
        return {
            "question": self.memory_thinking.load_memory_variables({}),
            "history": self.graph.get_node_details("start_node_id")  # 假设从初始节点开始
        }

    def get_graph_llm_input(self) -> dict:
        """
        获取传入 Graph LLM 的字典。

        返回:
            dict: 包含 Graph LLM 需要的输入数据。
        """
        return {
            "llm_input": self.graph.nodes,  # 假设 nodes 是图结构的表示
            "history": self.graph.get_node_details("start_node_id")
        }

    def get_action_llm_input(self) -> dict:
        """
        获取传入 Action LLM 的字典。

        返回:
            dict: 包含 Action LLM 需要的输入数据。
        """
        return {
            "Thought": self.graph.nodes,  # 假设 nodes 是图结构的表示
        }


# 示例用法
if __name__ == "__main__":
    pod = Pod(path="../resources/pod_graph.json")

    thinking_llm_input = pod.get_thinking_llm_input()
    graph_llm_input = pod.get_graph_llm_input()
    action_llm_input = pod.get_action_llm_input()

    print("Thinking LLM Input:", thinking_llm_input)
    print("Graph LLM Input:", graph_llm_input)
    print("Action LLM Input:", action_llm_input)
