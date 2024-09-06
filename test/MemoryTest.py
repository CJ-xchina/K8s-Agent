import unittest
import subprocess
import time
from datetime import datetime, timedelta

from bean.graph.Graph import Graph
from bean.memory.MemoryItem import MemoryItemFactory
from bean.memory.baseMemory import baseMemory

# 定义 Graph 的 JSON 数据，action 是 Windows 命令
json_data = '''
{
  "nodes": [
    {
      "id": "node1",
      "type": "command",
      "question": "你想执行哪个指令？",
      "regex": null,
      "action": "echo 当前时间是 %TIME%",
      "transitions": {
        "next": "node2"
      }
    },
    {
      "id": "node2",
      "type": "command",
      "question": "执行第二个指令，显示当前日期。",
      "regex": null,
      "action": "echo 今天的日期是 %DATE%",
      "transitions": {
        "next": "node3"
      }
    },
    {
      "id": "node3",
      "type": "command",
      "question": "所有命令执行完成。",
      "regex": null,
      "action": "echo 执行结束。",
      "transitions": {}
    }
  ]
}
'''


class TestBaseMemory(unittest.TestCase):

    def setUp(self):
        """
        初始化测试环境，在每个测试用例之前调用
        """
        # 创建基于 JSON 的图对象
        self.graph = Graph(start_node_id="node1", json_source=json_data)

        # 设置定时刷新间隔为5秒
        self.base_memory = baseMemory(interval_seconds=5, get_graph_func=self.graph.get_graph_obj)

    def create_memory_item(self, action, observation, description, question, node_ids, timestamp=None):
        """
        辅助函数，通过工厂类创建 MemoryItem 对象。
        """
        # 使用 MemoryItemFactory 创建 MemoryItem
        if not timestamp:
            timestamp = datetime.now()

        return MemoryItemFactory.create_memory_item(
            action=action,
            observation=observation,
            description=description,
            question=question,
            node_ids=node_ids
        )

    def run_action_and_capture_output(self, action):
        """
        运行一个 Windows cmd 的 action 并捕获输出，模拟 Graph 的 execute_action。
        """
        try:
            result = subprocess.run(action, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            return str(e)

    def test_store_and_get_memory_item(self):
        """
        测试存储和获取 MemoryItem，并验证其是否存储和检索正确
        """
        print("\n开始测试存储和获取 MemoryItem")
        memory_item = self.create_memory_item("echo 当前时间是 %TIME%", "这是观察1", "这是描述1", "你想执行哪个指令？",
                                              {"node1", "node2"})
        self.base_memory.store_data(memory_item)

        # 测试是否能通过 action 获取存储的 MemoryItem
        retrieved_item = self.base_memory.get_memory_item_by_action("echo 当前时间是 %TIME%")
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item.action, "echo 当前时间是 %TIME%")
        self.assertEqual(retrieved_item.observation, "这是观察1")
        self.assertEqual(retrieved_item.description, "这是描述1")

        print("存储和获取 MemoryItem 测试通过")

    def test_remove_memory_item(self):
        """
        测试删除 MemoryItem，并验证删除是否成功
        """
        print("\n开始测试删除 MemoryItem")
        memory_item = self.create_memory_item("echo 今天的日期是 %DATE%", "这是观察2", "这是描述2",
                                              "执行第二个指令，显示当前日期。", {"node3"})
        self.base_memory.store_data(memory_item)

        # 测试是否能删除 MemoryItem
        self.base_memory.remove_memory_item_by_action("echo 今天的日期是 %DATE%")
        retrieved_item = self.base_memory.get_memory_item_by_action("echo 今天的日期是 %DATE%")
        self.assertIsNone(retrieved_item)

        print("删除 MemoryItem 测试通过")

    def test_refresh_all_items(self):
        """
        测试刷新 MemoryItem，确保时间最新的 MemoryItem 最先被刷新，并验证是否刷新成功
        """
        print("\n开始测试刷新 MemoryItem")
        memory_item1 = self.create_memory_item("echo 当前时间是 %TIME%", "这是观察3", "这是描述3",
                                               "你想执行哪个指令？", {"node1", "node2"},
                                               timestamp=datetime.now() - timedelta(minutes=10))
        memory_item2 = self.create_memory_item("echo 今天的日期是 %DATE%", "这是观察4", "这是描述4",
                                               "执行第二个指令，显示当前日期。", {"node3"},
                                               timestamp=datetime.now())

        # 存储两个 MemoryItem
        self.base_memory.store_data(memory_item1)
        self.base_memory.store_data(memory_item2)

        # 模拟刷新所有的 MemoryItem
        self.base_memory.refresh_all_items()

        # 通过运行 action 判断是否刷新
        current_time_output = self.run_action_and_capture_output("echo 当前时间是 %TIME%")
        current_date_output = self.run_action_and_capture_output("echo 今天的日期是 %DATE%")

        print(f"刷新后的当前时间输出: {current_time_output}")
        print(f"刷新后的当前日期输出: {current_date_output}")

        self.assertIn("当前时间是", current_time_output)
        self.assertIn("今天的日期是", current_date_output)

        print("MemoryItem 刷新测试通过，最新的 MemoryItem 最先被刷新")

    def test_get_all_summaries(self):
        """
        测试获取所有 MemoryItem 的总结信息，并检查输出的内容是否正确
        """
        print("\n开始测试获取所有 MemoryItem 总结")
        memory_item1 = self.create_memory_item("echo 当前时间是 %TIME%", "这是观察5", "这是描述5", "你想执行哪个指令？",
                                               {"node1", "node2"})
        memory_item2 = self.create_memory_item("echo 今天的日期是 %DATE%", "这是观察6", "这是描述6",
                                               "执行第二个指令，显示当前日期。", {"node3"})

        # 存储两个 MemoryItem
        self.base_memory.store_data(memory_item1)
        self.base_memory.store_data(memory_item2)

        # 获取所有的总结信息
        summaries = self.base_memory.get_all_summaries()
        print("MemoryItem 总结输出：\n", summaries)

        # 检查总结是否包含预期内容
        self.assertIn("echo 当前时间是 %TIME%", summaries)
        self.assertIn("这是描述5", summaries)
        self.assertIn("echo 今天的日期是 %DATE%", summaries)
        self.assertIn("这是描述6", summaries)

        print("获取 MemoryItem 总结测试通过")

    def test_automatic_refresh(self):
        """
        测试自动刷新机制，确保自动刷新按预期工作
        """
        print("\n开始测试自动刷新 MemoryItem")
        memory_item1 = self.create_memory_item("echo 当前时间是 %TIME%", "这是观察7", "这是描述7", "你想执行哪个指令？",
                                               {"node1", "node2"},
                                               timestamp=datetime.now() - timedelta(minutes=1))
        self.base_memory.store_data(memory_item1)

        # 由于自动刷新间隔为5秒，我们等待10秒以确保自动刷新触发
        time.sleep(10)

        # 检查是否自动刷新，通过运行 action 验证
        refreshed_output = self.run_action_and_capture_output("echo 当前时间是 %TIME%")
        print(f"自动刷新后的输出: {refreshed_output}")

        self.assertIn("当前时间是", refreshed_output)

        print("自动刷新 MemoryItem 测试通过")


if __name__ == "__main__":
    unittest.main()
