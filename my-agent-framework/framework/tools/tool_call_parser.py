"""
tool_call_parser.py — Parse Tool Calls dari Model Output

Modul ini mengekstrak tool calls dari respons model LLM.
Mendukung beberapa format:
1. JSON block: ```json { "tool": "...", "parameters": {...} } ```
2. Qwen/OpenAI function call format: {"name": "...", "arguments": {...}}
3. ReAct format: Action: tool_name\nAction Input: {...}
4. Plain call: TOOL_CALL: tool_name(arg1="val1", ...)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("framework.tools.tool_call_parser")


@dataclass
class ParsedToolCall:
    """Hasil parsing satu tool call dari teks model."""
    tool_name: str
    arguments: Dict[str, Any]
    raw_text: str = ""
    confidence: float = 1.0  # 0.0–1.0


def _try_json_block(text: str) -> List[ParsedToolCall]:
    """
    Parse JSON tool call dari code block markdown.

    Format:
    ```json
    {"tool": "calculator", "parameters": {"expression": "15*27"}}
    ```
    atau:
    ```json
    [{"tool": "...", "parameters": {...}}, ...]
    ```
    """
    calls = []
    pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                if not isinstance(item, dict):
                    continue
                # Format 1: {"tool": "name", "parameters": {...}}
                if "tool" in item:
                    calls.append(ParsedToolCall(
                        tool_name=item["tool"],
                        arguments=item.get("parameters", item.get("arguments", {})),
                        raw_text=raw,
                    ))
                # Format 2: {"name": "name", "arguments": {...}}
                elif "name" in item:
                    args = item.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"input": args}
                    calls.append(ParsedToolCall(
                        tool_name=item["name"],
                        arguments=args,
                        raw_text=raw,
                    ))
        except json.JSONDecodeError:
            pass
    return calls


def _try_function_call_format(text: str) -> List[ParsedToolCall]:
    """
    Parse Qwen/Ollama function call format dari respons tanpa markdown.

    Format:
    {"name": "calculator", "arguments": {"expression": "15*27"}}
    """
    calls = []
    # Cari semua JSON object di teks (bukan dalam code block)
    pattern = r'\{[^{}]*"(?:name|tool)"[^{}]*\}'
    for match in re.finditer(pattern, text):
        raw = match.group(0)
        try:
            data = json.loads(raw)
            if "name" in data:
                args = data.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"input": args}
                calls.append(ParsedToolCall(
                    tool_name=data["name"],
                    arguments=args,
                    raw_text=raw,
                    confidence=0.9,
                ))
            elif "tool" in data:
                calls.append(ParsedToolCall(
                    tool_name=data["tool"],
                    arguments=data.get("parameters", {}),
                    raw_text=raw,
                    confidence=0.9,
                ))
        except json.JSONDecodeError:
            pass
    return calls


def _try_react_format(text: str) -> List[ParsedToolCall]:
    """
    Parse ReAct (Reasoning + Acting) format.

    Format:
    Action: calculator
    Action Input: {"expression": "15 * 27"}

    atau:
    Thought: Saya perlu menghitung...
    Action: calculator
    Action Input: 15 * 27
    """
    calls = []
    # Cari pattern Action: ... \n Action Input: ...
    pattern = r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(.+?)(?=\nObservation:|\nThought:|\nAction:|\Z)"
    for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
        tool_name = match.group(1).strip()
        raw_input = match.group(2).strip()

        # Coba parse sebagai JSON
        try:
            args = json.loads(raw_input)
            if not isinstance(args, dict):
                args = {"input": raw_input}
        except json.JSONDecodeError:
            # Gunakan raw string sebagai input
            args = {"input": raw_input}

        calls.append(ParsedToolCall(
            tool_name=tool_name,
            arguments=args,
            raw_text=match.group(0),
            confidence=0.85,
        ))
    return calls


def _try_toolcall_tag(text: str) -> List[ParsedToolCall]:
    """
    Parse format tag <tool_call>...</tool_call> yang digunakan beberapa model.

    Format (Qwen3):
    <tool_call>
    {"name": "calculator", "arguments": {"expression": "15*27"}}
    </tool_call>
    """
    calls = []
    pattern = r"<tool_call>\s*([\s\S]*?)\s*</tool_call>"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                tool_name = data.get("name") or data.get("tool")
                args = data.get("arguments") or data.get("parameters") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"input": args}
                if tool_name:
                    calls.append(ParsedToolCall(
                        tool_name=tool_name,
                        arguments=args,
                        raw_text=raw,
                        confidence=0.95,
                    ))
        except json.JSONDecodeError:
            pass
    return calls


def parse_tool_calls(text: str, known_tools: Optional[List[str]] = None) -> List[ParsedToolCall]:
    """
    Parse semua tool calls dari teks respons model.

    Coba semua format secara berurutan, prioritaskan yang lebih spesifik.
    Jika `known_tools` diberikan, filter hanya tool yang terdaftar.

    Args:
        text: Respons model yang mungkin mengandung tool calls.
        known_tools: Daftar nama tool yang valid. Jika None, tidak ada filter.

    Returns:
        List ParsedToolCall, bisa kosong jika tidak ada tool call.
    """
    if not text or not text.strip():
        return []

    all_calls: List[ParsedToolCall] = []

    # Coba semua parser, urutkan dari paling spesifik
    parsers = [
        _try_toolcall_tag,       # <tool_call> tag (Qwen3)
        _try_json_block,         # ```json block
        _try_react_format,       # ReAct format
        _try_function_call_format,  # plain JSON object
    ]

    for parser in parsers:
        try:
            found = parser(text)
            if found:
                all_calls.extend(found)
                break  # Gunakan parser pertama yang berhasil
        except Exception as e:
            logger.debug(f"Parser {parser.__name__} error: {e}")

    # Filter berdasarkan known_tools jika diberikan
    if known_tools and all_calls:
        filtered = [c for c in all_calls if c.tool_name in known_tools]
        if filtered:
            return filtered
        # Jika semua difilter, kembalikan yang asli (biarkan caller handle error)
        logger.debug(f"Tool calls found but none match known_tools: {[c.tool_name for c in all_calls]}")
        return all_calls

    return all_calls


def has_tool_call(text: str) -> bool:
    """
    Cek cepat apakah teks mengandung tool call (tanpa parse penuh).
    Berguna untuk decide apakah perlu parse lebih lanjut.
    """
    indicators = [
        "<tool_call>",
        "Action:",
        '"tool"',
        '"name"',
        "```json",
    ]
    return any(ind.lower() in text.lower() for ind in indicators)
