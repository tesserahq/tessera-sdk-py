"""Compatibility checks for MCP providers adopting Tessera metadata.

This module is intended for provider tests and migration tooling. It compares
captured ``tools/list`` and ``tools/call`` responses from before and after a
provider adopts the Tessera metadata contract. It does not execute tools,
register an MCP server, or enforce policy at runtime.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from .metadata import MCPMetadata, MetadataLimits, parse_mcp_metadata


class ConformanceViolation(BaseModel):
    """One provider compatibility problem found by a conformance check.

    ``code`` is stable enough for tests and automation, while ``message`` is a
    human-readable explanation. ``tool_name`` is absent for snapshot-level
    problems that cannot be attributed to one valid tool name.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    tool_name: str | None = None


class ConformanceReport(BaseModel):
    """Immutable result of checking an MCP provider migration.

    A report collects every problem it can find so a provider author can fix a
    migration in one pass. Inspect :attr:`compliant` for branching or call
    :meth:`raise_for_errors` in a test that should fail immediately.
    """

    model_config = ConfigDict(frozen=True)

    violations: tuple[ConformanceViolation, ...] = ()

    @property
    def compliant(self) -> bool:
        """Whether the compared provider snapshots are wire-compatible."""

        return not self.violations

    def raise_for_errors(self) -> None:
        """Raise ``ValueError`` containing all violations when non-compliant."""

        if self.violations:
            details = "; ".join(item.message for item in self.violations)
            raise ValueError(f"MCP provider contract is not compliant: {details}")


def check_provider_contract(
    *,
    tools_before: Sequence[Mapping[str, Any]],
    tools_after: Sequence[Mapping[str, Any]],
    results_before: Mapping[str, Mapping[str, Any]] | None = None,
    results_after: Mapping[str, Mapping[str, Any]] | None = None,
    limits: MetadataLimits | None = None,
) -> ConformanceReport:
    """Compare MCP provider snapshots before and after metadata adoption.

    The tool sequences are raw entries captured from ``tools/list``. The result
    mappings associate a tool name with a representative raw ``tools/call``
    result. The check verifies that:

    * existing tools were not removed;
    * existing ``outputSchema`` values did not change;
    * normal result fields (``content``, ``structuredContent``, and ``isError``)
      remain identical when both result snapshots are supplied; and
    * any new Tessera ``_meta`` payload is valid and transport-safe.

    Result snapshots are optional because discovery compatibility can be tested
    independently. Tools newly added to ``tools_after`` are allowed. The
    function returns all discovered violations instead of raising, which makes
    it suitable for assertions and CI diagnostics.

    This is not a security boundary and does not call tools or validate whether
    their domain events are semantically correct.
    """
    violations: list[ConformanceViolation] = []
    before_by_name = _tools_by_name(tools_before, violations, "before")
    after_by_name = _tools_by_name(tools_after, violations, "after")

    for name, before in before_by_name.items():
        after = after_by_name.get(name)
        if after is None:
            violations.append(
                ConformanceViolation(
                    code="tool_removed",
                    tool_name=name,
                    message=f"Tool {name!r} is missing after migration",
                )
            )
        elif before.get("outputSchema") != after.get("outputSchema"):
            violations.append(
                ConformanceViolation(
                    code="output_schema_changed",
                    tool_name=name,
                    message=f"Tool {name!r} changed its outputSchema",
                )
            )

    before_results = results_before or {}
    for name, result in (results_after or {}).items():
        _validate_result(name, result, limits, violations)
        baseline = before_results.get(name)
        if baseline is not None:
            for key in ("content", "structuredContent", "isError"):
                if baseline.get(key) != result.get(key):
                    violations.append(
                        ConformanceViolation(
                            code="normal_result_changed",
                            tool_name=name,
                            message=f"Tool {name!r} changed normal result field {key!r}",
                        )
                    )

    return ConformanceReport(violations=tuple(violations))


def _tools_by_name(
    tools: Sequence[Mapping[str, Any]],
    violations: list[ConformanceViolation],
    snapshot: str,
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for tool in tools:
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            violations.append(
                ConformanceViolation(
                    code="invalid_tool_name",
                    message=f"The {snapshot} tools snapshot contains an invalid name",
                )
            )
            continue
        if name in indexed:
            violations.append(
                ConformanceViolation(
                    code="duplicate_tool_name",
                    tool_name=name,
                    message=f"The {snapshot} snapshot repeats tool {name!r}",
                )
            )
        indexed[name] = tool
    return indexed


def _validate_result(
    name: str,
    result: Mapping[str, Any],
    limits: MetadataLimits | None,
    violations: list[ConformanceViolation],
) -> MCPMetadata | None:
    meta = result.get("_meta")
    if meta is None:
        return None
    if not isinstance(meta, Mapping):
        violations.append(
            ConformanceViolation(
                code="invalid_metadata",
                tool_name=name,
                message=f"Tool {name!r} returned non-object _meta",
            )
        )
        return None
    try:
        metadata = parse_mcp_metadata(meta, limits)
    except (TypeError, ValueError) as exc:
        violations.append(
            ConformanceViolation(
                code="invalid_metadata",
                tool_name=name,
                message=f"Tool {name!r} returned invalid metadata: {exc}",
            )
        )
        return None
    if (metadata.events or metadata.debug) and "structuredContent" not in result:
        violations.append(
            ConformanceViolation(
                code="missing_structured_content",
                tool_name=name,
                message=f"Tool {name!r} metadata requires structuredContent",
            )
        )
    return metadata
