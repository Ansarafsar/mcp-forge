"""Pydantic models describing an MCP-Forge spec (the YAML schema).

The spec is the single source of truth a developer writes. Everything else in
MCP-Forge consumes these models: the loader validates raw YAML against them and
the generator turns them into runnable Python.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Map of friendly YAML type names -> Python annotation names used in generated code.
TYPE_MAP: dict[str, str] = {
    "str": "str",
    "string": "str",
    "int": "int",
    "integer": "int",
    "float": "float",
    "number": "float",
    "bool": "bool",
    "boolean": "bool",
    "list": "list",
    "array": "list",
    "dict": "dict",
    "object": "dict",
    "any": "Any",
}


class ParameterSpec(BaseModel):
    """A single tool/prompt parameter."""

    name: str
    type: str = "str"
    description: Optional[str] = None
    default: Optional[Any] = None
    optional: bool = False
    # Only used when type == "enum".
    choices: Optional[list[Any]] = None

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"parameter name {v!r} is not a valid Python identifier")
        return v

    @model_validator(mode="after")
    def _check_type(self) -> "ParameterSpec":
        t = self.type.lower()
        if t == "enum":
            if not self.choices:
                raise ValueError(
                    f"parameter {self.name!r} has type 'enum' but no 'choices' listed"
                )
        elif t not in TYPE_MAP:
            allowed = ", ".join(sorted(set(TYPE_MAP) | {"enum"}))
            raise ValueError(
                f"parameter {self.name!r} has unknown type {self.type!r}. "
                f"Allowed types: {allowed}"
            )
        return self


class ToolSpec(BaseModel):
    """An MCP tool: a callable the model can invoke."""

    name: str
    description: str = ""
    params: list[ParameterSpec] = Field(default_factory=list)
    returns: str = "str"
    # Inline Python body. If omitted, a NotImplementedError stub is generated.
    body: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"tool name {v!r} is not a valid Python identifier")
        return v


class ResourceSpec(BaseModel):
    """An MCP resource: addressable data exposed at a URI."""

    name: str
    uri: str
    description: str = ""
    returns: str = "str"
    body: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"resource name {v!r} is not a valid Python identifier")
        return v


class PromptSpec(BaseModel):
    """An MCP prompt: a reusable, parameterized message template."""

    name: str
    description: str = ""
    params: list[ParameterSpec] = Field(default_factory=list)
    # The templated body. Rendered as an f-string, so `{param}` interpolates.
    template: str = ""

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"prompt name {v!r} is not a valid Python identifier")
        return v


class ForgeSpec(BaseModel):
    """Top-level spec: one YAML file == one MCP server."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    mcp_version: Optional[str] = None
    # Raw Python inserted at module level (imports, shared state, helpers).
    prelude: Optional[str] = None
    tools: list[ToolSpec] = Field(default_factory=list)
    resources: list[ResourceSpec] = Field(default_factory=list)
    prompts: list[PromptSpec] = Field(default_factory=list)

    @field_validator("mcp_version", "version", mode="before")
    @classmethod
    def _stringify(cls, v: Any) -> Any:
        # YAML parses bare dates/numbers (e.g. 2025-06-18) into non-str types.
        return None if v is None else str(v)

    @model_validator(mode="after")
    def _non_empty(self) -> "ForgeSpec":
        if not (self.tools or self.resources or self.prompts):
            raise ValueError(
                "spec defines no tools, resources, or prompts — nothing to generate"
            )
        return self
