"""
executor.py — Eksekusi Tool Calls

Executor bertanggung jawab menjalankan tool calls yang diminta
oleh agent, menangani error, retry, timeout, dan sandbox.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Any, Dict, List, Optional

logger = logging.getLogger("framework.loop.executor")


class ToolExecutionResult:
    """Hasil eksekusi satu tool call."""

    def __init__(
        self,
        tool_name: str,
        success: bool,
        output: Any,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ):
        self.tool_name = tool_name
        self.success = success
        self.output = output
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": str(self.output)[:2000],
            "error": self.error,
            "duration_ms": self.duration_ms,
        }

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"ToolResult({status} {self.tool_name}, {self.duration_ms:.0f}ms)"


class Executor:
    """
    Eksekutor tool calls dengan dukungan:
    - Sequential & parallel execution
    - Timeout per tool call
    - Retry otomatis
    - Sandboxing (blokir tools berbahaya)
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, Any]] = None,
        default_timeout: float = 30.0,
        max_retries: int = 2,
        max_workers: int = 4,
        blocked_tools: Optional[List[str]] = None,
    ):
        self.tool_registry: Dict[str, Any] = tool_registry or {}
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.blocked_tools: List[str] = blocked_tools or []
        self._execution_log: List[Dict] = []

    # ==================== TOOL REGISTRY ====================

    def register_tool(self, name: str, tool: Any) -> "Executor":
        """Daftarkan tool ke executor."""
        self.tool_registry[name] = tool
        logger.debug(f"Tool registered: '{name}'")
        return self

    def block_tool(self, name: str) -> "Executor":
        """Blokir tool agar tidak bisa dipanggil."""
        if name not in self.blocked_tools:
            self.blocked_tools.append(name)
        return self

    # ==================== EXECUTION ====================

    def execute(
        self,
        tool_name: str,
        tool_input: Dict,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> ToolExecutionResult:
        """
        Eksekusi satu tool call.

        Args:
            tool_name: Nama tool yang akan dipanggil.
            tool_input: Argumen tool.
            timeout: Timeout dalam detik (override default).
            retries: Jumlah retry (override default).

        Returns:
            ToolExecutionResult
        """
        timeout = timeout or self.default_timeout
        retries = retries if retries is not None else self.max_retries

        # Security: cek blokir
        if tool_name in self.blocked_tools:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=f"Tool '{tool_name}' diblokir oleh security policy",
            )

        # Cari tool
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=f"Tool '{tool_name}' tidak terdaftar. Tersedia: {list(self.tool_registry.keys())}",
            )

        # Eksekusi dengan retry
        last_error: Optional[str] = None
        for attempt in range(retries + 1):
            start = time.time()
            try:
                result = self._run_with_timeout(tool, tool_input, timeout)
                duration_ms = (time.time() - start) * 1000

                exec_result = ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    output=result,
                    duration_ms=duration_ms,
                )
                self._log(exec_result, tool_input)
                logger.info(f"Tool '{tool_name}' OK in {duration_ms:.0f}ms (attempt {attempt + 1})")
                return exec_result

            except TimeoutError:
                duration_ms = (time.time() - start) * 1000
                last_error = f"Timeout setelah {timeout}s"
                logger.warning(f"Tool '{tool_name}' timeout (attempt {attempt + 1})")

            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Tool '{tool_name}' error (attempt {attempt + 1}): {e}")

            if attempt < retries:
                wait = 0.5 * (2 ** attempt)  # Exponential backoff
                logger.debug(f"  Retry in {wait:.1f}s...")
                time.sleep(wait)

        # Semua attempt gagal
        exec_result = ToolExecutionResult(
            tool_name=tool_name,
            success=False,
            output=None,
            error=last_error,
            duration_ms=(time.time() - start) * 1000,
        )
        self._log(exec_result, tool_input)
        return exec_result

    def execute_batch(
        self,
        calls: List[Dict],
        parallel: bool = False,
        max_workers: Optional[int] = None,
    ) -> List[ToolExecutionResult]:
        """
        Eksekusi beberapa tool calls.

        Args:
            calls: List dict dengan keys: tool_name, tool_input.
            parallel: Jalankan secara paralel.
            max_workers: Override max thread workers.

        Returns:
            List ToolExecutionResult (urutan sesuai calls).
        """
        if parallel:
            return self._execute_parallel(calls, max_workers or self.max_workers)
        return self._execute_sequential(calls)

    def _execute_sequential(self, calls: List[Dict]) -> List[ToolExecutionResult]:
        """Eksekusi berurutan."""
        results = []
        for call in calls:
            result = self.execute(
                tool_name=call.get("tool_name", ""),
                tool_input=call.get("tool_input", {}),
                timeout=call.get("timeout"),
            )
            results.append(result)
            # Stop if critical failure
            if not result.success and call.get("critical", False):
                logger.warning(f"Critical tool '{result.tool_name}' failed — stopping batch")
                break
        return results

    def _execute_parallel(self, calls: List[Dict], max_workers: int) -> List[ToolExecutionResult]:
        """Eksekusi paralel dengan ThreadPoolExecutor."""
        results: List[Optional[ToolExecutionResult]] = [None] * len(calls)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, call in enumerate(calls):
                future = executor.submit(
                    self.execute,
                    call.get("tool_name", ""),
                    call.get("tool_input", {}),
                    call.get("timeout"),
                )
                futures[future] = i

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = ToolExecutionResult(
                        tool_name=calls[idx].get("tool_name", ""),
                        success=False,
                        output=None,
                        error=str(e),
                    )

        return [r for r in results if r is not None]

    def _run_with_timeout(self, tool: Any, tool_input: Dict, timeout: float) -> Any:
        """Jalankan tool dengan batas waktu menggunakan thread."""
        result_container: Dict = {"result": None, "error": None, "done": False}

        def target():
            try:
                if hasattr(tool, "run"):
                    result_container["result"] = tool.run(**tool_input)
                elif callable(tool):
                    result_container["result"] = tool(**tool_input)
                else:
                    result_container["error"] = f"Tool tidak callable"
            except Exception as e:
                result_container["error"] = e
            finally:
                result_container["done"] = True

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if not result_container["done"]:
            raise TimeoutError(f"Tool execution exceeded {timeout}s")
        if result_container["error"] is not None:
            raise result_container["error"] if isinstance(result_container["error"], Exception) \
                else Exception(result_container["error"])

        return result_container["result"]

    # ==================== LOGGING ====================

    def _log(self, result: ToolExecutionResult, tool_input: Dict):
        """Simpan log eksekusi."""
        entry = result.to_dict()
        entry["input_keys"] = list(tool_input.keys())
        self._execution_log.append(entry)
        if len(self._execution_log) > 500:
            self._execution_log.pop(0)

    def get_execution_log(self, last_n: int = 50) -> List[Dict]:
        """Ambil N log eksekusi terakhir."""
        return self._execution_log[-last_n:]

    def get_stats(self) -> Dict:
        """Statistik eksekusi."""
        total = len(self._execution_log)
        success = sum(1 for e in self._execution_log if e["success"])
        avg_ms = (
            sum(e["duration_ms"] or 0 for e in self._execution_log) / total
            if total > 0 else 0
        )
        return {
            "total_executions": total,
            "success": success,
            "failed": total - success,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_duration_ms": round(avg_ms, 1),
            "registered_tools": list(self.tool_registry.keys()),
            "blocked_tools": self.blocked_tools,
        }
