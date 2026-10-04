from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from .metadata import MCPMetadata, MetadataLimits, parse_mcp_metadata


class ConformanceViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    tool_name: str | None = None


class ConformanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    violations: tuple[ConformanceViolation, ...] = ()

    @property
    def compliant(self) -> bool:
        return not self.violations

    def raise_for_errors(self) -> None:
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
    """Compare provider snapshots and validate metadata-bearing call results."""
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
