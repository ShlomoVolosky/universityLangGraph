from dataclasses import dataclass, field

import sqlglot
import sqlglot.expressions as exp

_FORBIDDEN_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,  # covers ATTACH, PRAGMA, and other raw commands
)

_FORBIDDEN_FUNCTIONS = frozenset({"load_extension", "readfile", "writefile"})


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    is_non_select: bool = False


def validate(sql: str, dialect: str = "sqlite") -> ValidationResult:
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except sqlglot.errors.ParseError as exc:
        return ValidationResult(ok=False, errors=[f"Syntax error: {exc}"], is_non_select=False)

    if tree is None:
        return ValidationResult(ok=False, errors=["Empty statement."], is_non_select=False)

    # is_non_select = True only for unambiguously identified DML/DDL roots.
    # Garbled SQL that sqlglot "recovers" into an unrecognized node type
    # (e.g. Alias) is treated as a retryable syntax/parsing error.
    if isinstance(tree, _FORBIDDEN_NODE_TYPES):
        return ValidationResult(
            ok=False,
            errors=[f"Forbidden statement type: {type(tree).__name__}."],
            is_non_select=True,
        )

    # Root must be SELECT or CTE (WITH … SELECT)
    is_select_root = isinstance(tree, exp.Select) or (
        isinstance(tree, exp.With) and isinstance(tree.this, exp.Select)
    )
    if not is_select_root:
        # Not a known DML/DDL and not a SELECT — likely garbled SQL; retryable.
        node_type = type(tree).__name__
        return ValidationResult(
            ok=False,
            errors=[f"Statement is not a SELECT (got {node_type}); only SELECT is allowed."],
            is_non_select=False,
        )

    errors: list[str] = []

    # Walk descendants for any embedded forbidden statement types
    for node in tree.walk():
        if node is tree:
            continue
        if isinstance(node, _FORBIDDEN_NODE_TYPES):
            return ValidationResult(
                ok=False,
                errors=[f"Forbidden statement type in query: {type(node).__name__}."],
                is_non_select=True,
            )

    # Check for forbidden function calls by name
    for node in tree.walk():
        if isinstance(node, exp.Anonymous):
            if node.name.lower() in _FORBIDDEN_FUNCTIONS:
                errors.append(f"Forbidden function: {node.name}.")
        elif isinstance(node, exp.Func):
            fname = type(node).__name__.lower()
            if fname in _FORBIDDEN_FUNCTIONS:
                errors.append(f"Forbidden function: {fname}.")

    if errors:
        return ValidationResult(ok=False, errors=errors, is_non_select=False)

    return ValidationResult(ok=True)
