"""Unit tests for AST/regex symbol extraction."""
from __future__ import annotations

from app.domain.enums import SymbolKind
from app.infrastructure.code_intel.regex_symbols import extract_regex_symbols
from app.infrastructure.code_intel.symbol_extractor import extract_symbols

PY = '''\
import os
from app.auth import service


class AuthService:
    """Handles auth."""

    def login(self, email, password):
        return True


@router.post("/login")
async def login_endpoint(payload):
    return {}
'''


def _by_kind(symbols, kind):
    return [s for s in symbols if s.kind == kind]


def test_python_extracts_class_method_function_import_route():
    syms = extract_symbols(relative_path="app/auth/api.py", content=PY, language="python")
    classes = _by_kind(syms, SymbolKind.CLASS)
    methods = _by_kind(syms, SymbolKind.METHOD)
    functions = _by_kind(syms, SymbolKind.FUNCTION)
    imports = _by_kind(syms, SymbolKind.IMPORT)
    routes = _by_kind(syms, SymbolKind.ROUTE)

    assert any(c.name == "AuthService" for c in classes)
    assert any(m.name == "login" and m.parent_name == "AuthService" for m in methods)
    assert any(f.name == "login_endpoint" for f in functions)
    assert {i.name for i in imports} >= {"os", "app.auth"}
    assert any("POST /login" in r.name for r in routes)


def test_python_qualified_name_uses_module_path():
    syms = extract_symbols(relative_path="app/auth/api.py", content=PY, language="python")
    cls = next(s for s in syms if s.kind == SymbolKind.CLASS)
    assert cls.qualified_name == "app.auth.api.AuthService"


def test_python_syntax_error_returns_empty():
    assert extract_symbols(relative_path="x.py", content="def (:", language="python") == []


def test_regex_extracts_js_function_class_and_route():
    js = (
        "export class UserService {}\n"
        "export async function getUser(id) {}\n"
        "const make = (x) => x\n"
        "app.get('/users', handler)\n"
    )
    syms = extract_regex_symbols(js)
    names = {s.name for s in syms}
    assert "UserService" in names
    assert "getUser" in names
    assert "make" in names
    assert any(s.kind == SymbolKind.ROUTE and "GET /users" in s.name for s in syms)
