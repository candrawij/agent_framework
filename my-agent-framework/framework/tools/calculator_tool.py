"""
calculator_tool.py — Kalkulasi Matematis Aman

Tool untuk melakukan perhitungan matematis dari ekspresi string.
Menggunakan ast.literal_eval + custom evaluator — tidak menggunakan eval() langsung.
"""

import ast
import logging
import math
import operator
from typing import Any, Dict

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.calculator_tool")

# Operator yang diizinkan
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Fungsi matematika yang diizinkan
_ALLOWED_FUNCS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "pow": math.pow,
    "min": min,
    "max": max,
    "sum": sum,
}


def _safe_eval(node: ast.AST) -> Any:
    """Evaluasi AST node secara aman — hanya operator dan fungsi yang diizinkan."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Tipe konstanta tidak diizinkan: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Operator tidak diizinkan: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _ALLOWED_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Operator unary tidak diizinkan")
        return _ALLOWED_OPS[op_type](_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Hanya pemanggilan fungsi sederhana yang diizinkan")
        func_name = node.func.id
        if func_name not in _ALLOWED_FUNCS:
            raise ValueError(f"Fungsi tidak diizinkan: {func_name}")
        func = _ALLOWED_FUNCS[func_name]
        args = [_safe_eval(a) for a in node.args]
        return func(*args)
    elif isinstance(node, ast.Name):
        # Konstanta (pi, e)
        if node.id in _ALLOWED_FUNCS:
            val = _ALLOWED_FUNCS[node.id]
            if callable(val):
                raise ValueError(f"'{node.id}' adalah fungsi, bukan konstanta")
            return val
        raise ValueError(f"Nama tidak diizinkan: {node.id}")
    elif isinstance(node, ast.List):
        return [_safe_eval(el) for el in node.elts]
    else:
        raise ValueError(f"Node AST tidak diizinkan: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Kalkulasi ekspresi matematika secara aman."""

    name = "calculator"
    description = (
        "Hitung ekspresi matematika. Mendukung operasi dasar (+, -, *, /, **, %), "
        "fungsi (sqrt, sin, cos, tan, log, floor, ceil, round, factorial), "
        "dan konstanta (pi, e). Selalu gunakan tool ini untuk perhitungan — jangan hitung sendiri."
    )
    tags = ["math", "calculator", "utility"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": (
                        "Ekspresi matematika yang akan dihitung. "
                        "Contoh: '15 * 27', 'sqrt(144)', '2**10', 'sin(pi/2)', 'factorial(10)'"
                    ),
                },
                "precision": {
                    "type": "integer",
                    "description": "Jumlah desimal untuk pembulatan hasil (default: 10)",
                    "default": 10,
                },
            },
            "required": ["expression"],
        }

    def run(self, expression: str, precision: int = 10) -> str:
        # Bersihkan ekspresi
        expr = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
        expr = expr.replace(",", "")  # Hapus pemisah ribuan

        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree)

            # Format hasil
            if isinstance(result, float):
                if result == int(result) and abs(result) < 1e15:
                    result_str = str(int(result))
                else:
                    result_str = f"{round(result, precision):g}"
            elif isinstance(result, int):
                result_str = f"{result:,}".replace(",", ".")  # Format ribuan
            elif isinstance(result, complex):
                result_str = str(result)
            else:
                result_str = str(result)

            logger.info(f"Calculator: '{expr}' = {result_str}")
            return f"{expression} = {result_str}"

        except ZeroDivisionError:
            return f"❌ Error: Pembagian dengan nol"
        except ValueError as e:
            return f"❌ Ekspresi tidak valid: {e}"
        except SyntaxError:
            return f"❌ Sintaks ekspresi salah: '{expression}'"
        except OverflowError:
            return f"❌ Hasil terlalu besar untuk dihitung"
        except Exception as e:
            return f"❌ Gagal menghitung: {e}"
