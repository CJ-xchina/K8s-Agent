import asyncio
import re
from datetime import datetime
from time import sleep
from typing import Any, Dict, Optional, List

from langchain_core.agents import AgentAction

from utils.tools import execute_action


class QuestionRegexPair:
    """
    该类用于存储问题、正则表达式和结论的对应关系。
    """

    def __init__(self, question: str, regex: Optional[str] = None, conclusion: Optional[str] = None):
        """
        初始化 QuestionRegexPair 对象。

        Args:
            question (str): 问题，必须提供。
            regex (Optional[str]): 正则表达式，可选。如果未提供，则默认为 None。
            conclusion (Optional[str]): 结论，初始化时为空，之后更新。
        """
        self.question = question
        self.regex = regex
        self.conclusion = conclusion

    def to_dict(self) -> dict:
        """
        将 QuestionRegexPair 对象转换为字典格式，便于存储和序列化。

        Returns:
            dict: 包含问题、正则表达式和结论的字典。
        """
        return {
            "question": self.question,
            "regex": self.regex,
            "conclusion": self.conclusion
        }

    @staticmethod
    def from_dict(data: dict) -> 'QuestionRegexPair':
        """
        从字典中重建 QuestionRegexPair 对象。

        Args:
            data (dict): 包含问题、正则表达式和结论数据的字典。

        Returns:
            QuestionRegexPair: 生成的 QuestionRegexPair 对象。
        """
        question = data.get("question")
        regex = data.get("regex")
        conclusion = data.get("conclusion")
        return QuestionRegexPair(question=question, regex=regex, conclusion=conclusion)


class MemoryItem:
    """
    MemoryItem 类用于存储与某个动作（action）相关的观察、多个问题、正则表达式和结论的对应关系。
    """

    def __init__(self, action: AgentAction,
                 observation: str,
                 description: str,
                 question_regex_pairs: Optional[List[QuestionRegexPair]] = None,
                 timestamp: Optional[datetime] = None):
        """
        初始化 MemoryItem 对象。

        Args:
            action (AgentAction): 需要存储的动作对象。
            observation (str): 观察到的内容。
            description (str): 该条记忆的描述。
            question_regex_pairs (List[QuestionRegexPair], optional): 与问题和正则表达式对应的对象列表。
            timestamp (datetime, optional): 上次执行时间。默认使用当前时间。
        """
        self.action = action
        self.observation = observation
        self.description = description
        self.question_regex_pairs = question_regex_pairs if question_regex_pairs else []
        self.timestamp = timestamp if timestamp else datetime.now()

    def add_question_regex_pair(self, question: str, regex: Optional[str] = None):
        """
        向 MemoryItem 添加新的 QuestionRegexPair。如果 question 已存在，则不会添加。

        Args:
            question (str): 要添加的问题。
            regex (Optional[str]): 该问题的正则表达式，可选。
        """
        for pair in self.question_regex_pairs:
            if pair.question == question:
                print(f"Question '{question}' 已存在，不会重复添加。")
                return
        self.question_regex_pairs.append(QuestionRegexPair(question, regex))
        print(f"成功添加新的 question: '{question}' 和对应的 regex: '{regex}'")

    async def run_action_and_update(self, llm_extract_func: Optional[callable] = None):
        """
        异步执行动作，更新 Observation 和每个 QuestionRegexPair 的 Conclusion。
        如果正则表达式为空，则调用 LLM 提取关键信息。

        Args:
            llm_extract_func (callable, optional): 提供的 LLM 提取关键信息的异步函数，该函数接受 (result, question) 并返回提取的结论。
        """
        # 执行动作，获取结果
        result = execute_action(self.action)
        self.observation = result

        # Prepare tasks for concurrent execution
        tasks = []
        for pair in self.question_regex_pairs:
            if pair.regex:
                # Perform regex matching

                task = self.process_regex(result, pair)
            else:
                # Call the LLM extract function if no regex is provided
                if llm_extract_func:
                    task = llm_extract_func(result, pair.question)
                else:
                    task = self.handle_no_llm_func(pair.question)
            tasks.append(task)

        # Run tasks concurrently and collect results
        conclusions = await asyncio.gather(*tasks, return_exceptions=True)

        # Update each pair with its conclusion
        for idx, pair in enumerate(self.question_regex_pairs):
            if isinstance(conclusions[idx], Exception):
                pair.conclusion = str(conclusions[idx])
            else:
                pair.conclusion = conclusions[idx]

        # 更新最后执行时间
        self.timestamp = datetime.now()

    async def process_regex(self, result: str, pair: QuestionRegexPair) -> str:
        """
        使用正则表达式处理结果，并返回匹配的结论。

        Args:
            result (str): 动作执行的结果。
            pair (QuestionRegexPair): 包含问题和正则表达式的对象。

        Returns:
            str: 正则匹配到的结论，或者返回匹配失败信息。
        """
        # await asyncio.sleep(10)
        # # 返回当前时间的字符串形式
        # return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        match = re.search(pair.regex, result)
        if match:
            return match.group(0)  # Return matched result as conclusion
        else:
            return f"正则表达式匹配失败: '{pair.question}'"

    async def handle_no_llm_func(self, question: str) -> str:
        """
        处理没有提供 LLM 提取函数的情况，返回提示信息。

        Args:
            question (str): 未提供 LLM 提取函数时的问题。

        Returns:
            str: 处理后的提示信息。
        """
        return f"LLM 提取所需的函数未提供，问题: {question}"

    def to_dict(self) -> Dict[str, Any]:
        """
        将 MemoryItem 对象转换为字典格式，便于存储和序列化。

        Returns:
            Dict[str, Any]: 包含动作、观察、结论、描述、正则表达式、问题和时间戳的字典。
        """
        return {
            "action": str(self.action),  # 假设 `AgentAction` 有字符串表示
            "observation": self.observation,
            "description": self.description,
            "question_regex_pairs": [pair.to_dict() for pair in self.question_regex_pairs],
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(item_dict: Dict[str, Any]) -> 'MemoryItem':
        """
        从字典中重建 MemoryItem 对象。

        Args:
            item_dict (Dict[str, Any]): 存储数据的字典。

        Returns:
            MemoryItem: 生成的 MemoryItem 对象。
        """
        timestamp = datetime.fromisoformat(item_dict["timestamp"])
        action = item_dict["action"]
        if isinstance(action, dict):
            action = AgentAction.from_dict(action)  # 假设 `AgentAction` 有 `from_dict` 方法

        question_regex_pairs = [QuestionRegexPair.from_dict(pair) for pair in item_dict["question_regex_pairs"]]

        return MemoryItem(
            action=action,
            observation=item_dict["observation"],
            description=item_dict["description"],
            question_regex_pairs=question_regex_pairs,
            timestamp=timestamp
        )

    def __repr__(self):
        return (f"MemoryItem(Action: {self.action}, Observation: {self.observation}, "
                f"Description: {self.description}, Questions: {[pair.question for pair in self.question_regex_pairs]})")
