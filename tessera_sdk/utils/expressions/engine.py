from __future__ import annotations

from typing import Any, Dict
from jinja2 import Environment
from tessera_sdk.utils.expressions.soft_undefined import SoftUndefined


class ExpressionEngine:
    """
    Simple wrapper around Jinja2:
    - Plain Jinja syntax: {{ json... }}, {{ node... }}, {{ env... }}
    - Missing variables never raise; they render as "".
    """

    def __init__(self) -> None:
        self.env = Environment(
            undefined=SoftUndefined,
            autoescape=False,
        )
        self._register_default_filters()

    def _register_default_filters(self) -> None:
        # Minimal, safe filters. Add more as needed.

        # {{ value | upper }}
        self.env.filters["upper"] = lambda v: v.upper() if isinstance(v, str) else v

        # {{ value | default('N/A') }}
        def default_filter(value: Any, default_value: Any = "") -> Any:
            if value is None:
                return default_value
            if isinstance(value, SoftUndefined):
                return default_value
            if value == "":
                return default_value
            return value

        self.env.filters["default"] = default_filter

    # ---------- public API ----------

    def render(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Render a template string using given context.

        Example context:
          {
              "json": trigger_payload,
              "node": {
                  "Trigger": {"json": trigger_payload},
                  "FetchAccount": {"json": fetch_account_output},
              },
              "env": {
                  "BASE_URL": "https://api.example.com",
              },
          }

        Missing variables become empty strings.
        """
        template = self.env.from_string(template_str)
        return template.render(context)
