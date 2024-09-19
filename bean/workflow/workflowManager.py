import asyncio
from typing import Dict, Optional, Any, List
from bean.workflow.baseWorkFlow import Workflow


class WorkflowManager:
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.tasks: Dict[str, asyncio.Task] = {}  # 存储所有工作流的任务
        self.new_tasks_event = asyncio.Event()  # 事件，用于通知新增任务

    def create_workflow(self, current_node_id: str, context: Dict[str, Any] = None) -> Workflow:
        """
        创建一个新的工作流，并返回该工作流实例。
        """
        workflow = Workflow(current_node_id, context)
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def add_workflow(self, workflow: Workflow):
        """
        添加已有的工作流实例。
        """
        self.workflows[workflow.workflow_id] = workflow

    def remove_workflow(self, workflow_id: str):
        """
        移除指定的工作流，并取消关联的任务。
        """
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
        if workflow_id in self.tasks:
            task = self.tasks[workflow_id]
            if not task.done():
                task.cancel()  # 取消未完成的任务
            del self.tasks[workflow_id]

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        获取指定 ID 的工作流。
        """
        return self.workflows.get(workflow_id)

    def get_all_workflows(self) -> List[Workflow]:
        """
        获取所有工作流。
        """
        return list(self.workflows.values())

    def add_task(self, workflow_id: str, task: asyncio.Task):
        """
        将任务添加到任务字典中，并触发新任务事件。
        """
        self.tasks[workflow_id] = task
        self.new_tasks_event.set()  # 通知有新任务

    def get_task(self, workflow_id: str) -> Optional[asyncio.Task]:
        """
        获取指定工作流 ID 的任务。
        """
        return self.tasks.get(workflow_id)

    async def run_all_tasks(self):
        """
        并行运行所有任务，持续监测并处理新增任务，直到所有任务完成。
        """
        while True:
            if not self.tasks:
                break  # 如果没有任务则退出

            # 等待所有现有任务完成或有新的任务加入
            pending_tasks = [task for task in self.tasks.values() if not task.done()]
            if not pending_tasks:
                break  # 所有任务都完成，退出循环

            self.new_tasks_event.clear()  # 清除新任务事件
            done, _ = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

            # 处理已完成的任务
            for task in done:
                if task.exception():
                    print(f"Task {task} raised an exception: {task.exception()}")

            # 如果有新的任务加入，则继续监测
            await self.new_tasks_event.wait()
