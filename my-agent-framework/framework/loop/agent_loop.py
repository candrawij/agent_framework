"""
agent_loop.py — Orchestrator Utama Siklus Agent

AgentLoop mengatur siklus lengkap:
Plan → Execute → Observe → Reflect → (Repeat / Done)

Ini adalah komponen pusat yang menghubungkan semua bagian loop.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional

from .planner import Planner, Task, TaskStatus
from .executor import Executor, ToolExecutionResult
from .observer import Observer, Observation
from .reflector import Reflector, ReflectionOutcome

logger = logging.getLogger("framework.loop.agent_loop")


@dataclass
class LoopRunResult:
    """Hasil lengkap satu run loop."""
    session_id: str
    goal: str
    final_answer: str
    outcome: str             # "done" | "failed" | "timeout"
    iterations: int
    tasks_completed: int
    tasks_failed: int
    observations: List[Dict] = field(default_factory=list)
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "goal": self.goal[:100],
            "final_answer": self.final_answer[:500],
            "outcome": self.outcome,
            "iterations": self.iterations,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


class AgentLoop:
    """
    Orchestrator utama siklus agent.

    Flow untuk satu request:
    1. Planner: Decompose goal → task list
    2. Executor: Jalankan setiap task (tool calls / agent calls)
    3. Observer: Proses hasil → observasi terstruktur
    4. Reflector: Evaluasi apakah selesai
    5. Ulangi atau selesai

    Thread-safe untuk concurrent requests.
    """

    def __init__(
        self,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        observer: Optional[Observer] = None,
        reflector: Optional[Reflector] = None,
        supervisor: Optional[Any] = None,   # SupervisorAgent
        memory_manager: Optional[Any] = None,
        model_manager: Optional[Any] = None,  # ModelManager — fallback jika tidak ada supervisor
        max_iterations: int = 10,
        on_iteration_callback: Optional[Callable] = None,
    ):
        self.planner = planner or Planner()
        self.executor = executor or Executor()
        self.observer = observer or Observer()
        self.reflector = reflector or Reflector()
        self.supervisor = supervisor
        self.memory_manager = memory_manager
        self.model_manager = model_manager
        self.max_iterations = max_iterations
        self.on_iteration_callback = on_iteration_callback

    # ==================== MAIN RUN ====================

    def run(
        self,
        goal: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
        use_planning: bool = True,
    ) -> LoopRunResult:
        """
        Jalankan full agent loop untuk satu goal.

        Args:
            goal: Goal yang ingin dicapai.
            session_id: ID sesi (untuk tracking).
            context: Konteks tambahan (memory, history, dll).
            use_planning: Gunakan Planner untuk decompose goal.

        Returns:
            LoopRunResult dengan hasil lengkap.
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())[:8]
        context = context or {}
        start_time = time.time()

        logger.info(f"[{session_id}] AgentLoop starting — goal='{goal[:80]}'")

        # Inject memory ke context jika ada
        if self.memory_manager:
            try:
                context["memory"] = self.memory_manager.get_relevant(goal)
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {e}")

        # 1. PLANNING
        if use_planning:
            tasks = self.planner.plan(goal, context)
        else:
            from .planner import Task
            tasks = [Task(name="direct", description=goal, input=goal)]

        logger.info(f"[{session_id}] Plan: {len(tasks)} tasks")

        # 2. EXECUTION LOOP
        observations: List[Observation] = []
        completed_ids: List[str] = []
        final_answer: str = ""
        iterations = 0
        tasks_completed = 0
        tasks_failed = 0

        for iteration in range(self.max_iterations):
            iterations = iteration + 1
            ready_tasks = [t for t in tasks if t.is_ready(completed_ids) and t.status == TaskStatus.PENDING]

            if not ready_tasks:
                logger.info(f"[{session_id}] No more ready tasks at iteration {iterations}")
                break

            logger.debug(f"[{session_id}] Iteration {iterations}: {len(ready_tasks)} ready tasks")

            for task in ready_tasks:
                task.status = TaskStatus.RUNNING

                # 2a. EXECUTE task
                result = self._execute_task(task, context, observations)

                # 2b. OBSERVE
                if result["success"]:
                    obs = self.observer.observe(
                        source=task.name,
                        raw_output=result["output"],
                        metadata={"task_id": task.id},
                    )
                    task.status = TaskStatus.DONE
                    task.result = result["output"]
                    completed_ids.append(task.id)
                    observations.append(obs)
                    tasks_completed += 1
                    final_answer = str(result["output"])
                else:
                    obs = self.observer.observe_error(task.name, result.get("error", "Unknown"))
                    task.status = TaskStatus.FAILED
                    task.error = result.get("error")
                    completed_ids.append(task.id)
                    observations.append(obs)
                    tasks_failed += 1

            # 2c. REFLECT
            reflection = self.reflector.evaluate(
                goal=goal,
                observations=observations,
                last_response=final_answer,
                iteration=iteration,
                max_iterations=self.max_iterations,
            )

            logger.info(
                f"[{session_id}] Reflection: {reflection.outcome.value} "
                f"(confidence={reflection.confidence:.2f})"
            )

            # Callback untuk streaming/UI updates
            if self.on_iteration_callback:
                try:
                    self.on_iteration_callback({
                        "session_id": session_id,
                        "iteration": iterations,
                        "reflection": reflection.to_dict(),
                        "last_answer": final_answer,
                    })
                except Exception:
                    pass

            # Simpan ke memory jika ada
            if self.memory_manager and observations:
                try:
                    self.memory_manager.add(
                        content=final_answer,
                        source="agent_loop",
                        metadata={"session": session_id, "goal": goal[:100]},
                    )
                except Exception as e:
                    logger.debug(f"Memory save failed: {e}")

            if reflection.outcome != ReflectionOutcome.CONTINUE:
                break

        duration_ms = (time.time() - start_time) * 1000

        # Tentukan outcome akhir
        if tasks_failed > 0 and tasks_completed == 0:
            outcome = "failed"
        elif iterations >= self.max_iterations:
            outcome = "timeout"
        else:
            outcome = "done"

        result = LoopRunResult(
            session_id=session_id,
            goal=goal,
            final_answer=final_answer or "[Tidak ada hasil]",
            outcome=outcome,
            iterations=iterations,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            observations=[o.to_dict() for o in observations],
            duration_ms=duration_ms,
        )

        logger.info(
            f"[{session_id}] Loop done: outcome={outcome}, "
            f"{iterations} iters, {duration_ms:.0f}ms"
        )
        return result

    def stream(
        self,
        goal: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Iterator[str]:
        """
        Streaming agent loop — yield update per iterasi.

        Args:
            goal: Goal yang ingin dicapai.
            session_id: ID sesi.
            context: Konteks tambahan.

        Yields:
            String update per iterasi atau token.
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())[:8]
        context = context or {}
        streamed_updates: List[str] = []

        def on_iteration(data: Dict):
            update = (
                f"\n[Iterasi {data['iteration']}] "
                f"Status: {data['reflection']['outcome']}\n"
            )
            streamed_updates.append(update)

        self.on_iteration_callback = on_iteration

        # Jalankan di thread terpisah
        import threading
        result_container: Dict = {}

        def run():
            result_container["result"] = self.run(goal, session_id, context)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        # Stream updates
        yielded_count = 0
        while thread.is_alive() or yielded_count < len(streamed_updates):
            if yielded_count < len(streamed_updates):
                yield streamed_updates[yielded_count]
                yielded_count += 1
            else:
                time.sleep(0.1)

        # Yield final answer
        if "result" in result_container:
            yield f"\n\n{result_container['result'].final_answer}"

    # ==================== HELPERS ====================

    def _execute_task(
        self, task: Task, context: Dict, observations: List[Observation]
    ) -> Dict:
        """Eksekusi satu task — pilih antara tool, agent, atau supervisor."""
        try:
            # Jika ada tool_name, gunakan executor
            if task.tool_name:
                tool_result: ToolExecutionResult = self.executor.execute(
                    tool_name=task.tool_name,
                    tool_input={"input": task.input} if not isinstance(task.input, dict) else task.input,
                )
                return {"success": tool_result.success, "output": tool_result.output, "error": tool_result.error}

            # Jika ada agent_name, gunakan registry
            if task.agent_name and self.supervisor:
                obs_context = context.copy()
                obs_context["history"] = [o.to_dict() for o in observations[-3:]]
                output = self.supervisor.registry.get(task.agent_name)
                if output:
                    result = output.execute(str(task.input), obs_context)
                    return {"success": True, "output": result}

            # Fallback: gunakan supervisor
            if self.supervisor:
                obs_context = context.copy()
                obs_context["history"] = [o.to_dict() for o in observations[-3:]]
                output = self.supervisor.execute(str(task.input), obs_context)
                return {"success": True, "output": output}

            # Fallback: langsung ke ModelManager (Sprint 1b)
            # Digunakan ketika belum ada supervisor/tool terdaftar
            if self.model_manager:
                # Siapkan messages dengan context history jika ada
                messages = []
                if context.get("messages"):
                    messages = context["messages"]
                else:
                    messages = [{"role": "user", "content": str(task.input)}]

                logger.info(f"Task '{task.name}': no tool/supervisor, falling back to model_manager")
                result = self.model_manager.complete(
                    messages=messages,
                    temperature=context.get("temperature", 0.7),
                )
                content = result.get("content", "")
                if content:
                    return {"success": True, "output": content}
                return {"success": False, "error": "Model returned empty response", "output": None}

            return {"success": False, "error": "Tidak ada executor/supervisor/model_manager tersedia", "output": None}

        except Exception as e:
            logger.error(f"Task '{task.name}' execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "output": None}

    def get_stats(self) -> Dict:
        """Statistik komponen loop."""
        return {
            "executor": self.executor.get_stats(),
            "observer": self.observer.get_stats(),
            "max_iterations": self.max_iterations,
        }
