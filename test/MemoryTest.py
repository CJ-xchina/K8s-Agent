import json
import time
from datetime import datetime
from unittest.mock import MagicMock

from langchain_core.agents import AgentAction

from bean.memory.MemoryItem import QuestionRegexPair, MemoryItem
from bean.memory.baseMemory import baseMemory


# 假设 MemoryItem.py 和 baseMemory.py 已经导入
# from MemoryItem import MemoryItem, QuestionRegexPair
# from baseMemory import BaseMemory

# 测试 QuestionRegexPair
def test_question_regex_pair():
    print("=== 测试 QuestionRegexPair ===")
    question = "你的名字是什么？"
    regex = r"\w+"

    # 创建 QuestionRegexPair 对象
    qrp = QuestionRegexPair(question=question, regex=regex)

    # 测试 to_dict 方法
    qrp_dict = qrp.to_dict()
    print(f"字典形式：{qrp_dict}")

    # 测试 from_dict 方法
    qrp_rebuilt = QuestionRegexPair.from_dict(qrp_dict)
    print(f"重建后的对象：问题: {qrp_rebuilt.question}, 正则表达式: {qrp_rebuilt.regex}")
    print("\n")


# 测试 MemoryItem
def test_memory_item():
    print("=== 测试 MemoryItem ===")

    # 创建模拟的 AgentAction 对象（此处用 MagicMock 代替实际的 AgentAction）
    mock_action = MagicMock()

    l1 = QuestionRegexPair("1", "1", "1")
    l2 = QuestionRegexPair("2", "2", "2")
    l3 = QuestionRegexPair("3", "3", "3")

    list = [l1, l2, l3]
    # 初始化 MemoryItem
    memory_item = MemoryItem(
        action=mock_action,
        observation="观察到用户点击了按钮。",
        description="记录一次按钮交互。",
        question_regex_pairs=list,

        timestamp=datetime.now()
    )

    # 测试 to_dict 方法
    memory_item_dict = memory_item.to_dict()
    print(f"MemoryItem 字典形式：{json.dumps(memory_item_dict, ensure_ascii=False, indent=2)}")


# 测试 BaseMemory
def test_base_memory():
    print("=== 测试 BaseMemory ===")

    # 创建 BaseMemory 对象
    base_memory = baseMemory(5)

    l1 = QuestionRegexPair("1", "1", "1")
    l2 = QuestionRegexPair("2", "2", "2")
    l3 = QuestionRegexPair("3", "3", "3")

    list = [l1, l2, l3]
    # 创建模拟的 MemoryItem 对象
    mock_action = AgentAction("kubectl_command", "echo hello,","3")
    memory_item = MemoryItem(
        action=mock_action,
        observation="观察到用户滚动页面。",
        description="记录一次页面滚动事件。",
        timestamp=datetime.now(),
        question_regex_pairs=list
    )

    # 将 MemoryItem 添加到 BaseMemory
    base_memory.store_data(memory_item)
    print("添加了 MemoryItem 到 BaseMemory。")

    time.sleep(20)
    # 测试获取所有存储的数据
    all_data = base_memory.get_data()
    print(f"获取到的存储数据：{json.dumps(json.loads(all_data), ensure_ascii=False, indent=2)}")

    print("\n")


# 运行测试
if __name__ == "__main__":
    test_question_regex_pair()
    test_memory_item()
    test_base_memory()
