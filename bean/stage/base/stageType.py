from enum import Enum


class StageType(Enum):
    """
    StageType枚举类，用于表示Stage的类型。

    可能的值包括：
    - THINKING: 表示思考阶段
    - ACTION: 表示行动阶段
    - OBSERVATION: 表示观察阶段
    """
    THINKING = "Thinking"
    TOLL = "Toll"
    OBSERVATION = "Observation"

