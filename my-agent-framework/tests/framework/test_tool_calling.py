"""
test_tool_calling.py — Test untuk Tools dan Plugins

Refactored dari saki_ai_assistant/tests/test_plugins.py
"""
import pytest
from pathlib import Path
import tempfile
import os

from framework.tools.base_tool import BaseTool
from framework.tools.file_io import ReadFileTool, WriteFileTool, ListFolderTool
from framework.tools.shell_command import GetSystemInfoTool


class ConcreteTool(BaseTool):
    name = "concrete_tool"
    description = "Test tool"
    def run(self, **kwargs): return f"ok: {kwargs}"


class TestBaseTool:
    def test_get_schema(self):
        tool = ConcreteTool()
        schema = tool.get_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "concrete_tool"

    def test_safe_run_success(self):
        tool = ConcreteTool()
        result = tool.safe_run(x=1)
        assert result["success"]
        assert result["output"] is not None

    def test_get_info(self):
        tool = ConcreteTool()
        info = tool.get_info()
        assert info["name"] == "concrete_tool"


class TestFileIOTools:
    def test_read_nonexistent(self):
        tool = ReadFileTool()
        result = tool.run(path="/nonexistent/path/file.txt")
        assert "tidak ditemukan" in result.lower() or "❌" in result

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            write_tool = WriteFileTool()
            result = write_tool.run(path=filepath, content="Hello Framework")
            assert "✅" in result

            read_tool = ReadFileTool()
            content = read_tool.run(path=filepath)
            assert "Hello Framework" in content

    def test_list_folder(self):
        tool = ListFolderTool()
        result = tool.run(path=str(Path.home()))
        assert "📂" in result

    def test_list_nonexistent_folder(self):
        tool = ListFolderTool()
        result = tool.run(path="/nonexistent/folder/xyz")
        assert "❌" in result


class TestSystemInfo:
    def test_get_system_info(self):
        tool = GetSystemInfoTool()
        result = tool.run()
        assert "OS" in result or "os" in result.lower()
