import asyncio
import logging
from typing import Set

from bean.graph.Node import Node
from bean.memory.NodeMemoryItem import QuestionNodePair
from bean.resources.pod import Pod
from bean.stage.base.BaseStage import BaseStage
from utils.str_utils import process_regex
from utils.tools import execute_action


class StageUtils:
    """
    StageUtils 工具类负责处理与 stage 相关的逻辑，包括执行动作、提取结论、并发控制等。
    """

    @staticmethod
    async def run_action_and_set_conclusion(pair: QuestionNodePair, extract_stage: BaseStage, pod: Pod,
                                            max_concurrency: int = 5):
        """
        统一处理动作的执行和提取结论，支持并发控制。

        Args:
            pair (QuestionNodePair): 问题与节点的映射。
            extract_stage (BaseStage): 提取逻辑的执行阶段。
            max_concurrency (int): 最大并发任务数量。
            pod: 与节点关联的 Pod 对象。
        """
        # 获取任意一个节点的 action，因为所有 node 的 action 相同
        first_node = next(iter(next(iter(pair.question_node_map.values()))))
        action = first_node.action

        # 执行动作，获取结果
        observation = execute_action(action)

        # 创建并发任务列表
        tasks = []

        # 信号量控制并发任务的数量
        semaphore = asyncio.Semaphore(max_concurrency)

        # 遍历 question 和对应的 nodes，构建任务
        for question, nodes in pair.question_node_map.items():
            tasks.append(
                StageUtils._process_question_nodes(observation, question, nodes,
                                                   extract_stage, semaphore, pod))

        try:
            # 并发执行所有任务，限制并发数
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"任务执行过程中出现错误: {e}")

    @staticmethod
    async def _process_question_nodes(observation: str, question: str, nodes: Set[Node],
                                      extract_stage: BaseStage, semaphore: asyncio.Semaphore,
                                      pod):
        """
        处理单个问题及其所有节点，获取结论并更新对应的 Node 对象。

        Args:
            observation (str): 执行动作的结果。
            question (str): 问题字符串。
            nodes (Set[Node]): 与问题关联的节点对象集合。
            extract_stage (BaseStage): 提取阶段。
            semaphore (asyncio.Semaphore): 并发控制的信号量。
            pod: 与节点关联的 Pod 对象。
        """
        async with semaphore:
            try:
                first_node = next(iter(nodes))

                if first_node.regex:
                    # 使用正则表达式进行匹配
                    conclusion = await process_regex(observation, first_node.regex)
                else:
                    # 提取模式并处理输入
                    patterns = first_node.get_node_if_statement()
                    input_map = {
                        "raw_input": observation,
                        "question": question,
                        "details": pod.get_info()
                    }
                    action, conclusion = extract_stage.set_patterns_before_step(patterns, input_map)

                # 更新所有节点的结论
                for node in nodes:
                    node.conclusion = conclusion

            except Exception as e:
                logging.error(f"处理节点 '{first_node.node_id}' 时出错: {e}")
