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
        tool_registry: Optional[Any] = None,  # ToolRegistry — Sprint 7
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
        self.tool_registry = tool_registry
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
        """
        Eksekusi satu task dengan ReAct loop:
        1. Jika task.tool_name langsung → eksekusi tool
        2. Jika ada model_manager → kirim ke model, parse tool calls dari respons
           Ulangi hingga model menghasilkan jawaban final (tanpa tool call)
        3. Fallback ke supervisor jika ada
        """
        try:
            # --- Eksekusi langsung jika tool_name sudah ditentukan ---
            if task.tool_name:
                if self.tool_registry:
                    result = self.tool_registry.execute(
                        task.tool_name,
                        {"input": task.input} if not isinstance(task.input, dict) else task.input,
                    )
                    return {"success": result["success"], "output": result["output"], "error": result.get("error")}
                else:
                    tool_result: ToolExecutionResult = self.executor.execute(
                        tool_name=task.tool_name,
                        tool_input={"input": task.input} if not isinstance(task.input, dict) else task.input,
                    )
                    return {"success": tool_result.success, "output": tool_result.output, "error": tool_result.error}

            # --- Supervisor ---
            if task.agent_name and self.supervisor:
                obs_context = context.copy()
                obs_context["history"] = [o.to_dict() for o in observations[-3:]]
                output = self.supervisor.registry.get(task.agent_name)
                if output:
                    result = output.execute(str(task.input), obs_context)
                    return {"success": True, "output": result}

            if self.supervisor:
                obs_context = context.copy()
                obs_context["history"] = [o.to_dict() for o in observations[-3:]]
                output = self.supervisor.execute(str(task.input), obs_context)
                return {"success": True, "output": output}

            # --- ReAct Loop dengan ModelManager + ToolRegistry ---
            if self.model_manager:
                from framework.tools.tool_call_parser import parse_tool_calls, has_tool_call

                # Siapkan messages awal
                messages: List[Dict] = []
                if context.get("messages"):
                    messages = list(context["messages"])
                else:
                    messages = [{"role": "user", "content": str(task.input)}]

                # Siapkan system prompt dengan tool descriptions jika ada tool_registry
                tool_schemas = []
                known_tool_names = []
                if self.tool_registry:
                    tool_schemas = self.tool_registry.get_schemas()
                    known_tool_names = self.tool_registry.list_names()

                if tool_schemas and not any(m["role"] == "system" for m in messages):
                    tools_desc = "\n".join(
                        f"- {s['function']['name']}: {s['function']['description']}"
                        for s in tool_schemas
                    )
                    system_msg = (
                        "Kamu adalah asisten AI dengan akses ke tools berikut:\n"
                        f"{tools_desc}\n\n"
                        "Untuk menggunakan tool, tulis dalam format:\n"
                        "<tool_call>\n"
                        '{"name": "nama_tool", "arguments": {"param": "nilai"}}\n'
                        "</tool_call>\n\n"
                        "Setelah mendapat hasil tool, gunakan hasilnya untuk menjawab user."
                    )
                    messages = [{"role": "system", "content": system_msg}] + messages

                # ReAct loop — maksimal 5 iterasi tool calling
                tool_trace: List[Dict] = []
                for react_iter in range(5):
                    logger.info(f"Task '{task.name}': ReAct iter {react_iter + 1}, messages={len(messages)}")

                    result = self.model_manager.complete(
                        messages=messages,
                        temperature=context.get("temperature", 0.7),
                    )
                    content = result.get("content", "")
                    if not content:
                        return {"success": False, "error": "Model returned empty response", "output": None}

                    # Cek apakah ada tool call
                    if not (self.tool_registry and has_tool_call(content)):
                        # Tidak ada tool call → ini jawaban final
                        logger.info(f"Task '{task.name}': final answer after {react_iter + 1} ReAct iters")
                        return {"success": True, "output": content, "tool_trace": tool_trace}

                    # Parse tool calls
                    tool_calls = parse_tool_calls(content, known_tools=known_tool_names)
                    if not tool_calls:
                        # Ada indikasi tool call tapi tidak bisa di-parse → anggap final answer
                        return {"success": True, "output": content, "tool_trace": tool_trace}

                    # Tambahkan respons model ke messages
                    messages.append({"role": "assistant", "content": content})

                    # Eksekusi semua tool calls dan kumpulkan hasilnya
                    tool_results_text = []
                    for tc in tool_calls:
                        logger.info(f"Executing tool: {tc.tool_name}({tc.arguments})")
                        exec_result = self.tool_registry.execute(tc.tool_name, tc.arguments)

                        trace_entry = {
                            "tool": tc.tool_name,
                            "arguments": tc.arguments,
                            "success": exec_result["success"],
                            "output": str(exec_result.get("output", ""))[:500],
                            "error": exec_result.get("error"),
                            "duration_ms": exec_result.get("duration_ms"),
                        }
                        tool_trace.append(trace_entry)

                        if exec_result["success"]:
                            tool_results_text.append(
                                f"Tool '{tc.tool_name}' result: {exec_result['output']}"
                            )
                        else:
                            tool_results_text.append(
                                f"Tool '{tc.tool_name}' error: {exec_result['error']}"
                            )

                    # Inject hasil tool ke messages sebagai 'tool' role
                    tool_result_content = "\n".join(tool_results_text)
                    messages.append({"role": "user", "content": f"Hasil tool:\n{tool_result_content}\n\nSekarang jawab pertanyaan user berdasarkan hasil di atas."})

                # Jika loop habis, ambil jawaban terakhir
                final_result = self.model_manager.complete(messages=messages)
                return {"success": True, "output": final_result.get("content", ""), "tool_trace": tool_trace}

            return {"success": False, "error": "Tidak ada model_manager tersedia", "output": None}

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
