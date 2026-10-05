from collections.abc import Iterable

ORIGIN_TAG_PREFIX = "origin:"


def get_origin(tags: Iterable[str] | None) -> str | None:
    """Return the single origin value, rejecting ambiguous origin metadata."""
    origins = [
        tag.removeprefix(ORIGIN_TAG_PREFIX)
        for tag in tags or ()
        if tag.startswith(ORIGIN_TAG_PREFIX)
    ]
    if len(origins) > 1:
        raise ValueError("At most one origin:* tag is allowed")
    if origins and not origins[0]:
        raise ValueError("The origin tag must contain a value")
    return origins[0] if origins else None


def set_origin(tags: Iterable[str] | None, origin: str) -> list[str]:
    """Return tags with exactly one normalized origin tag."""
    value = origin.removeprefix(ORIGIN_TAG_PREFIX).strip()
    if not value:
        raise ValueError("Origin must be a non-empty string")
    preserved = [tag for tag in tags or () if not tag.startswith(ORIGIN_TAG_PREFIX)]
    return [*preserved, f"{ORIGIN_TAG_PREFIX}{value}"]
