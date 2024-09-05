from bean.stage.ActionStage import ActionStage
from langchain.memory import ConversationBufferMemory

from bean.stage.ActionMemoryStage import ActionMemoryStage, MemoryStrategy
from bean.stage.stageType import StageType


class ToolStageMemoryStrategy(MemoryStrategy):
    def save_memory(self, memory: ConversationBufferMemory, input_str: str, output_str: str):
        # ToolStage 只保存输出内容，不保存输入内容
        memory.save_context({"input": ""}, {"output": output_str})

    def load_memory(self, memory: ConversationBufferMemory) -> dict:
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


class ActionAnalyzeStage:
    """
    ActionAnalyzeStage 类用于分析和执行指定的操作。它接受一个 ToolStageMemoryStrategy 对象，
    并且定义了一个_step方法，用于根据传入的正则表达式或动作执行相应的操作。

    Attributes:
        memory_strategy (ToolStageMemoryStrategy): 用于管理记忆策略的对象。
    """

    def __init__(self, memory_strategy: ToolStage):
        """
        初始化 ActionAnalyzeStage 类。

        Args:
            memory_strategy (ToolStage): 阶段对象。
        """
        self.memory_strategy = memory_strategy

    def _step(self, reg: Optional[str] = None, action: Optional[Union['AgentAction', str]] = None):
        """
        执行给定的操作。根据传入的正则表达式 (reg) 和 AgentAction 或 字符串 (action) 进行处理。

        Args:
            reg (str, optional): 正则表达式，用于匹配输入。如果为空，则执行默认操作。
            action (AgentAction or str, optional): 执行的动作，可以是一个动作对象或一个简单的字符串。

        Returns:
            str: 执行结果的描述。
        """
        # 如果 reg 为空，执行默认的分析逻辑
        if reg is None:
            return "默认操作已执行。"

        # 如果 reg 不为空，检查 action 的类型并处理
        if isinstance(action, AgentAction):
            # 执行 AgentAction 类型的操作
            return f"AgentAction 已执行，动作名称: {action.name}"
        elif isinstance(action, str):
            # 执行字符串类型的操作
            return f"字符串操作已执行，内容: {action}"
        else:
            return "未知的操作类型。"

# Example usage:
# memory_strategy = ToolStageMemoryStrategy()
# analyze_stage = ActionAnalyzeStage(memory_strategy)
# result = analyze_stage._step(reg=None, action="Some string action")
# print(result)

