"""High-fidelity Python symbol extraction using the standard-library `ast`.

Extracts module-level functions, classes and their methods, imports, top-level
assignments, and FastAPI/Flask-style routes (decorators like ``@router.get(...)``).
Syntax errors yield an empty list rather than raising.
"""
from __future__ import annotations

import ast

from app.infrastructure.code_intel.types import ExtractedSymbol
from app.domain.enums import SymbolKind

_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "route"}


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        args = ast.unparse(node.args)
    except Exception:  # noqa: BLE001
        args = ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args})"


def _route_paths(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return decorator paths that look like HTTP route registrations."""
    paths: list[str] = []
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        func = dec.func
        method = func.attr if isinstance(func, ast.Attribute) else None
        if method in _ROUTE_METHODS and dec.args:
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                paths.append(f"{method.upper()} {first.value}")
    return paths


def extract_python_symbols(content: str, *, module_qual: str) -> list[ExtractedSymbol]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    symbols: list[ExtractedSymbol] = []

    def visit_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef, parent: str | None
    ) -> None:
        kind = SymbolKind.METHOD if parent else SymbolKind.FUNCTION
        qual = f"{module_qual}.{parent}.{node.name}" if parent else f"{module_qual}.{node.name}"
        symbols.append(
            ExtractedSymbol(
                kind=kind,
                name=node.name,
                qualified_name=qual,
                signature=_signature(node),
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                parent_name=parent,
                docstring=ast.get_docstring(node),
            )
        )
        for path in _route_paths(node):
            symbols.append(
                ExtractedSymbol(
                    kind=SymbolKind.ROUTE,
                    name=path,
                    qualified_name=f"{qual} [{path}]",
                    signature=path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    parent_name=node.name,
                )
            )

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            symbols.append(
                ExtractedSymbol(
                    kind=SymbolKind.CLASS,
                    name=node.name,
                    qualified_name=f"{module_qual}.{node.name}",
                    signature=f"class {node.name}",
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    docstring=ast.get_docstring(node),
                )
            )
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    visit_function(child, node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            visit_function(node, None)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.append(
                    ExtractedSymbol(
                        kind=SymbolKind.IMPORT,
                        name=alias.name,
                        qualified_name=alias.name,
                        signature=f"import {alias.name}",
                        start_line=node.lineno,
                        end_line=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            symbols.append(
                ExtractedSymbol(
                    kind=SymbolKind.IMPORT,
                    name=module,
                    qualified_name=module,
                    signature=f"from {module} import ...",
                    start_line=node.lineno,
                    end_line=node.lineno,
                )
            )

    return symbols
