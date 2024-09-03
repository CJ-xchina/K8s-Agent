from bean.stage.ActionStage import ActionStage
from langchain.memory import ConversationBufferMemory

from bean.stage.ActionMemoryStage import ActionMemoryStage, MemoryStrategy
from bean.stage.stageType import StageType


class ToolStageMemoryStrategy(MemoryStrategy):
    def save_memory(self, memory: ConversationBufferMemory, input_str: str, output_str: str):
        # ToolStage 只保存输出内容，不保存输入内容
        memory.save_context({}, {"output": output_str})
        print(f"ToolStage Memory saved: Output: {output_str}")

    def load_memory(self, memory: ConversationBufferMemory) -> dict:
        # ToolStage 通常不需要读取记忆，返回空字典
        print("ToolStage does not load memory.")
        return {}


class ToolStage(ActionMemoryStage):
    """
    EnhancedActionStage 类继承自 ActionStage，增加了 name 和 description 属性。

    Attributes:
        name (str): 该阶段的名称。
        description (str): 该阶段的描述。
    """

    def __init__(self,
                 name: str,
                 description: str,
                 **kwargs):
        """
        初始化 EnhancedActionStage 类。

        Args:
            name (str): 阶段的名称。
            description (str): 阶段的描述。
            **kwargs: 传递给父类 ActionStage 的其他参数。
        """
        self.name = name
        self.description = description
        super().__init__(**kwargs)

    def get_stage_type(self) -> StageType:
        """
        获取当前 Stage 的类型。

        Returns:
            str: 当前 Stage 的类型（例如 "ToolStage" 或 "ThinkingStage"）。
        """
        return StageType.TOLL

    def get_memory_strategy(self) -> MemoryStrategy:
        return ToolStageMemoryStrategy()

    def get_name(self) -> str:
        """
        获取阶段的名称。

        Returns:
            str: 阶段的名称。
        """
        return self.name

    def get_description(self) -> str:
        """
        获取阶段的描述。

        Returns:
            str: 阶段的描述。
        """
        return self.description
