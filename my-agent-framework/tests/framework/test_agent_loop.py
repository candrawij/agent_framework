"""
test_agent_loop.py — Test untuk Agent Loop

Refactored dari saki_ai_assistant/tests/test_agents.py
"""
import pytest
from unittest.mock import MagicMock, patch

from framework.agents.base_agent import BaseAgent
from framework.agents.agent_registry import AgentRegistry
from framework.loop.planner import Planner, Task, TaskStatus
from framework.loop.executor import Executor


class ConcreteAgent(BaseAgent):
    """Implementasi konkret untuk testing."""
    def can_handle(self, message, context=None): return True
    def execute(self, message, context=None): return f"Result: {message}"


class TestBaseAgent:
    def test_init(self):
        agent = ConcreteAgent("test", "Test agent")
        assert agent.name == "test"
        assert agent.enabled is True
        assert agent.tools == []

    def test_enable_disable(self):
        agent = ConcreteAgent("test", "desc")
        agent.disable()
        assert not agent.enabled
        agent.enable()
        assert agent.enabled

    def test_log_execution(self):
        agent = ConcreteAgent("test", "desc")
        agent.log_execution("hello", "world", 100.0)
        history = agent.get_history()
        assert len(history) == 1
        assert history[0]["message"] == "hello"

    def test_execute(self):
        agent = ConcreteAgent("test", "desc")
        result = agent.execute("hello")
        assert "Result: hello" in result

    def test_get_info(self):
        agent = ConcreteAgent("test", "Test agent")
        info = agent.get_info()
        assert info["name"] == "test"
        assert "enabled" in info


class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        agent = ConcreteAgent("agent1", "desc")
        reg.register(agent)
        assert reg.get("agent1") is agent

    def test_enable_disable(self):
        reg = AgentRegistry()
        agent = ConcreteAgent("agent1", "desc")
        reg.register(agent)
        reg.disable("agent1")
        assert not agent.enabled
        reg.enable("agent1")
        assert agent.enabled

    def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(ConcreteAgent("a", "A"))
        reg.register(ConcreteAgent("b", "B"))
        agents = reg.list_agents()
        assert len(agents) == 2

    def test_unregister(self):
        reg = AgentRegistry()
        agent = ConcreteAgent("agent1", "desc")
        reg.register(agent)
        reg.unregister("agent1")
        assert reg.get("agent1") is None


class TestPlanner:
    def test_plan_simple(self):
        planner = Planner()
        tasks = planner.plan("Do something")
        assert len(tasks) == 1
        assert tasks[0].name == "main_task"

    def test_sequential_plan(self):
        planner = Planner()
        tasks = planner.create_sequential_plan([
            {"name": "step1", "description": "First step"},
            {"name": "step2", "description": "Second step"},
        ])
        assert len(tasks) == 2
        assert tasks[0].name == "step1"
        assert tasks[1].name == "step2"
        assert tasks[0].id in tasks[1].depends_on

    def test_parallel_plan(self):
        planner = Planner()
        tasks = planner.create_parallel_plan([
            {"name": "task_a"},
            {"name": "task_b"},
        ])
        assert len(tasks) == 2
        assert tasks[0].depends_on == []
        assert tasks[1].depends_on == []


class TestExecutor:
    def test_register_tool(self):
        executor = Executor()
        mock_tool = MagicMock()
        mock_tool.run = lambda x: f"result: {x}"
        executor.register_tool("mock", mock_tool)
        assert "mock" in executor.tool_registry

    def test_block_tool(self):
        executor = Executor()
        executor.block_tool("dangerous_tool")
        result = executor.execute("dangerous_tool", {})
        assert not result.success
        assert "diblokir" in result.error

    def test_execute_missing_tool(self):
        executor = Executor()
        result = executor.execute("nonexistent", {})
        assert not result.success
        assert "tidak terdaftar" in result.error.lower()
