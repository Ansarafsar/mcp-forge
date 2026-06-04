"""MCP-Forge: compile a YAML spec into a runnable MCP server."""

from __future__ import annotations

__version__ = "0.1.0"

from .generator import generate
from .loader import SpecError, load_spec
from .spec import ForgeSpec

__all__ = ["__version__", "ForgeSpec", "SpecError", "generate", "load_spec"]
