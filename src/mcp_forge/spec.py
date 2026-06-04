"""Pydantic models describing an MCP-Forge spec (the YAML schema).

The spec is the single source of truth a developer writes. Everything else in
MCP-Forge consumes these models: the loader validates raw YAML against them and
the generator turns them into runnable Python.
"""

from __future__ import annotations

import difflib
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
            choices = sorted(set(TYPE_MAP) | {"enum"})
            hint = difflib.get_close_matches(t, choices, n=1)
            suggestion = f" Did you mean {hint[0]!r}?" if hint else ""
            raise ValueError(
                f"parameter {self.name!r} has unknown type {self.type!r}.{suggestion} "
                f"Allowed types: {', '.join(choices)}"
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


class RateRule(BaseModel):
    """A token-bucket rate limit: *rate* calls allowed per *per* seconds."""

    rate: int = Field(gt=0)
    per: float = Field(default=60.0, gt=0)


class RateLimitSpec(BaseModel):
    """Rate-limit configuration: a default plus optional per-tool overrides."""

    default: Optional[RateRule] = None
    per_tool: dict[str, RateRule] = Field(default_factory=dict)


class ObservabilitySpec(BaseModel):
    """Logging, rate limiting, and audit forwarding."""

    logging: bool = False
    rate_limit: Optional[RateLimitSpec] = None
    # Optional URL to POST structured call logs to (e.g. an MCP-Audit endpoint).
    audit_url: Optional[str] = None


class AuthSpec(BaseModel):
    """Auth gate applied to every tool call."""

    type: str = "api_key"  # api_key | bearer_token | oauth_stub
    # Environment variable that must hold the expected secret/token.
    env: str = "MCP_API_KEY"
    # Informational: the header a remote transport would carry the secret in.
    header: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        allowed = {"api_key", "bearer_token", "oauth_stub"}
        if v not in allowed:
            raise ValueError(
                f"auth type {v!r} is not supported. Allowed: {', '.join(sorted(allowed))}"
            )
        return v


class ForgeSpec(BaseModel):
    """Top-level spec: one YAML file == one MCP server."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    mcp_version: Optional[str] = None
    # Raw Python inserted at module level (imports, shared state, helpers).
    prelude: Optional[str] = None
    auth: Optional[AuthSpec] = None
    observability: Optional[ObservabilitySpec] = None
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
