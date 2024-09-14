from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class RecordMemoryItem:
    """
    ObservationRecord 类用于存储与某个观察相关的信息。

    属性:
        id (str): 唯一标识符。
        parentId (Optional[str]): 父级记录的ID，如果有的话。
        observation (str): 观察的内容。
        timestamp (datetime): 记录的时间戳。
        llm_times (int): LLM（语言模型）调用的次数。
        start_time (datetime): 记录开始的时间。
        end_time (datetime): 记录结束的时间。
    """
    id: str
    parentId: Optional[str] = None
    observation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    llm_times: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        将 ObservationRecord 对象转换为字典格式，便于序列化和存储。

        Returns:
            dict: 包含所有属性的字典。
        """
        return {
            "id": self.id,
            "parentId": self.parentId,
            "observation": self.observation,
            "timestamp": self.timestamp.isoformat(),
            "llm_times": self.llm_times,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RecordMemoryItem':
        """
        从字典中创建 ObservationRecord 对象。

        Args:
            data (dict): 包含 ObservationRecord 数据的字典。

        Returns:
            ObservationRecord: 创建的 ObservationRecord 对象。
        """
        return RecordMemoryItem(
            id=data["id"],
            parentId=data.get("parentId"),
            observation=data.get("observation", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            llm_times=data.get("llm_times", 0),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
        )

    def update_observation(self, new_observation: str, llm_times: int):
        """
        更新 observation 内容，并更新时间戳和结束时间。

        Args:
            new_observation (str): 新的观察内容。
        """
        self.observation = new_observation
        self.timestamp = datetime.now()
        self.end_time = datetime.now()
        self.llm_times = llm_times

    def increment_llm_times(self):
        """
        增加 llm_times 计数。
        """
        self.llm_times += 1
        print(f"LLM times incremented for ID {self.id} to {self.llm_times}.")
