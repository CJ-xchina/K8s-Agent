from langchain.memory import ConversationBufferMemory

from bean.stage.ActionMemoryStage import ActionMemoryStage, MemoryStrategy
from bean.stage.stageType import StageType


class ThinkingStageMemoryStrategy(MemoryStrategy):
    def save_memory(self, memory: ConversationBufferMemory, input_str: str, output_str: str):
        # ThinkingStage 的策略可能不保存任何内容
        print("ThinkingStage does not save memory.")

    def load_memory(self, memory: ConversationBufferMemory) -> dict:
        # 读取最近的一次 Memory 消息
        memory_data = memory.load_memory_variables({})
        print(f"ThinkingStage Memory loaded: {memory_data}")
        return memory_data


class ThinkingStage(ActionMemoryStage):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_stage_type(self) -> StageType:
        """
        获取当前 Stage 的类型。

        Returns:
            str: 当前 Stage 的类型（例如 "ToolStage" 或 "ThinkingStage"）。
        """
        return StageType.THINKING

    def get_memory_strategy(self) -> MemoryStrategy:
        return ThinkingStageMemoryStrategy()
