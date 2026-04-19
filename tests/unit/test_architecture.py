"""
Mechanically enforce the hexagonal dependency rule:
  domain  → (nothing)
  ports   → domain only
  agent   → ports + domain only
  adapters → anything (they face infrastructure)

No code in domain/, ports/, or agent/ may import from adapters/.
Violation == test failure.
"""

import ast
import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

import pytest

SRC_ROOT = Path(__file__).parent.parent.parent / "src" / "university_qa"
ADAPTERS_PREFIX = "university_qa.adapters"


def _collect_modules(package: str) -> list[ModuleType]:
    """Import every module under `package` and return them."""
    root = importlib.import_module(package)
    modules = [root]
    root_path = Path(root.__file__).parent  # type: ignore[arg-type]
    for info in pkgutil.walk_packages([str(root_path)], prefix=package + "."):
        modules.append(importlib.import_module(info.name))
    return modules


def _ast_imports(module: ModuleType) -> list[str]:
    """Return all top-level import targets found in the module's source file."""
    src_file = getattr(module, "__file__", None)
    if src_file is None or not src_file.endswith(".py"):
        return []
    tree = ast.parse(Path(src_file).read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


@pytest.mark.parametrize(
    "package",
    [
        "university_qa.domain",
        "university_qa.ports",
        "university_qa.agent",
    ],
)
def test_no_adapter_imports(package: str) -> None:
    """No module inside domain/, ports/, or agent/ may import from adapters/."""
    violations: list[str] = []
    for module in _collect_modules(package):
        for imp in _ast_imports(module):
            if imp.startswith(ADAPTERS_PREFIX) or imp == "university_qa.adapters":
                violations.append(f"{module.__name__} imports {imp}")

    assert violations == [], (
        "Dependency rule violated — these modules import from adapters:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_ports_do_not_import_agent() -> None:
    """ports/ must not import from agent/."""
    violations: list[str] = []
    for module in _collect_modules("university_qa.ports"):
        for imp in _ast_imports(module):
            if imp.startswith("university_qa.agent"):
                violations.append(f"{module.__name__} imports {imp}")
    assert violations == []


def test_domain_has_no_infra_imports() -> None:
    """domain/ must not import LangGraph, LangChain, DB libs, or HTTP clients."""
    forbidden_prefixes = ("langgraph", "langchain", "sqlite3", "anthropic", "httpx", "requests")
    violations: list[str] = []
    for module in _collect_modules("university_qa.domain"):
        for imp in _ast_imports(module):
            for prefix in forbidden_prefixes:
                if imp == prefix or imp.startswith(prefix + "."):
                    violations.append(f"{module.__name__} imports {imp}")
    assert violations == [], "domain/ must be infrastructure-free:\n" + "\n".join(
        f"  {v}" for v in violations
    )
