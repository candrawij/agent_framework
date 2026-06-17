"""
planner.py — Task Decomposition & Dependency Graph

Planner bertanggung jawab memecah goal kompleks menjadi
sub-task yang lebih kecil, membentuk dependency graph,
dan menentukan urutan eksekusi optimal.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("framework.loop.planner")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Representasi satu unit pekerjaan."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    agent_name: Optional[str] = None   # Target agent (None = auto-route)
    tool_name: Optional[str] = None    # Atau langsung ke tool tertentu
    input: Any = None                  # Input untuk agent/tool
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    priority: int = 0                  # Semakin tinggi = semakin prioritas
    metadata: Dict = field(default_factory=dict)

    def is_ready(self, completed_ids: List[str]) -> bool:
        """Cek apakah semua dependency sudah selesai."""
        return all(dep in completed_ids for dep in self.depends_on)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "has_result": self.result is not None,
        }


class Planner:
    """
    Decomposisi goal menjadi sub-task dengan dependency graph.

    Alur:
    1. Terima goal (string atau dict)
    2. Optionally gunakan LLM untuk decompose (model_adapter)
    3. Bangun task graph
    4. Kembalikan ordered task list ke Executor
    """

    def __init__(self, model_adapter: Optional[Any] = None):
        self.model_adapter = model_adapter
        self._task_graph: Dict[str, Task] = {}

    # ==================== PLANNING ====================

    def plan(
        self,
        goal: str,
        context: Optional[Dict] = None,
        use_model: bool = False,
    ) -> List[Task]:
        """
        Buat rencana eksekusi untuk goal yang diberikan.

        Args:
            goal: Deskripsi goal yang ingin dicapai.
            context: Konteks tambahan (available agents, dll).
            use_model: Gunakan LLM untuk decompose (butuh model_adapter).

        Returns:
            Ordered list of Tasks.
        """
        self._task_graph.clear()

        if use_model and self.model_adapter:
            tasks = self._decompose_with_model(goal, context or {})
        else:
            # Simple: satu task tunggal
            tasks = [Task(name="main_task", description=goal, input=goal)]

        for task in tasks:
            self._task_graph[task.id] = task

        ordered = self._topological_sort()
        logger.info(f"Plan created: {len(ordered)} tasks for goal='{goal[:60]}'")
        return ordered

    def add_task(self, task: Task) -> "Planner":
        """Tambahkan task secara manual ke graph."""
        self._task_graph[task.id] = task
        return self

    def create_sequential_plan(self, tasks_data: List[Dict]) -> List[Task]:
        """
        Buat rencana sequential (task berikutnya bergantung ke sebelumnya).

        Args:
            tasks_data: List dict dengan keys: name, description, agent_name, input.

        Returns:
            Ordered task list.
        """
        self._task_graph.clear()
        previous_id: Optional[str] = None

        for data in tasks_data:
            task = Task(
                name=data.get("name", "task"),
                description=data.get("description", ""),
                agent_name=data.get("agent_name"),
                tool_name=data.get("tool_name"),
                input=data.get("input"),
                depends_on=[previous_id] if previous_id else [],
                priority=data.get("priority", 0),
            )
            self._task_graph[task.id] = task
            previous_id = task.id

        return self._topological_sort()

    def create_parallel_plan(self, tasks_data: List[Dict]) -> List[Task]:
        """
        Buat rencana paralel (semua task bisa jalan bersamaan).

        Args:
            tasks_data: List dict task.

        Returns:
            Task list (semua PENDING, tanpa dependency).
        """
        self._task_graph.clear()
        tasks = []
        for data in tasks_data:
            task = Task(
                name=data.get("name", "task"),
                description=data.get("description", ""),
                agent_name=data.get("agent_name"),
                input=data.get("input"),
            )
            self._task_graph[task.id] = task
            tasks.append(task)
        return tasks

    # ==================== HELPERS ====================

    def _decompose_with_model(self, goal: str, context: Dict) -> List[Task]:
        """Gunakan LLM untuk decompose goal menjadi sub-tasks."""
        available_agents = context.get("available_agents", [])
        agents_str = ", ".join(available_agents) if available_agents else "general"

        prompt = (
            f"Pecah goal berikut menjadi sub-task yang spesifik.\n"
            f"Goal: {goal}\n"
            f"Agent tersedia: {agents_str}\n\n"
            "Format JSON:\n"
            '[{"name": "...", "description": "...", "agent_name": "...", '
            '"depends_on": []}]\n'
            "Jawab HANYA JSON array."
        )

        try:
            import json
            response = self.model_adapter.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.get("content", "[]")
            # Extract JSON
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content.strip())
            if isinstance(data, list):
                return [
                    Task(
                        name=d.get("name", "task"),
                        description=d.get("description", ""),
                        agent_name=d.get("agent_name"),
                        depends_on=d.get("depends_on", []),
                        input=d.get("input", goal),
                    )
                    for d in data
                ]
        except Exception as e:
            logger.warning(f"Model decomposition failed: {e}. Falling back to single task.")

        return [Task(name="main_task", description=goal, input=goal)]

    def _topological_sort(self) -> List[Task]:
        """Urutkan task berdasarkan dependency (Kahn's algorithm)."""
        in_degree: Dict[str, int] = {tid: 0 for tid in self._task_graph}
        adjacency: Dict[str, List[str]] = {tid: [] for tid in self._task_graph}

        for tid, task in self._task_graph.items():
            for dep in task.depends_on:
                if dep in adjacency:
                    adjacency[dep].append(tid)
                    in_degree[tid] += 1

        queue = sorted(
            [tid for tid, deg in in_degree.items() if deg == 0],
            key=lambda t: -self._task_graph[t].priority,
        )
        result: List[Task] = []

        while queue:
            current = queue.pop(0)
            result.append(self._task_graph[current])
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort(key=lambda t: -self._task_graph[t].priority)

        if len(result) != len(self._task_graph):
            logger.warning("Cycle detected in task graph — some tasks may be skipped")

        return result

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._task_graph.get(task_id)

    def get_graph_summary(self) -> Dict:
        return {
            "total_tasks": len(self._task_graph),
            "tasks": [t.to_dict() for t in self._task_graph.values()],
        }
