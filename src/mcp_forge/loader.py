"""Load and validate a YAML spec into a :class:`ForgeSpec`.

Errors are turned into readable messages with line numbers where possible, so a
malformed spec points the developer straight at the problem.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .spec import ForgeSpec


class SpecError(Exception):
    """Raised when a spec file cannot be read, parsed, or validated."""


def load_spec(path: str | Path) -> ForgeSpec:
    """Read a YAML file at *path* and return a validated :class:`ForgeSpec`.

    Raises :class:`SpecError` with a friendly message on any failure.
    """
    p = Path(path)
    if not p.exists():
        raise SpecError(f"spec file not found: {p}")
    if not p.is_file():
        raise SpecError(f"spec path is not a file: {p}")

    text = p.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        problem = getattr(exc, "problem", str(exc))
        raise SpecError(f"invalid YAML in {p.name}{where}: {problem}") from exc

    if data is None:
        raise SpecError(f"{p.name} is empty")
    if not isinstance(data, dict):
        raise SpecError(
            f"{p.name} must be a YAML mapping at the top level, got {type(data).__name__}"
        )

    try:
        return ForgeSpec.model_validate(data)
    except ValidationError as exc:
        raise SpecError(_format_validation_error(p.name, exc)) from exc


def _format_validation_error(filename: str, exc: ValidationError) -> str:
    lines = [f"spec {filename} is invalid:"]
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "<root>"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
