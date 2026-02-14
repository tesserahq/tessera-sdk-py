"""User model mixin for shared user columns and hybrid properties.

Services can compose their own User model by inheriting from UserMixin
along with their Base and other mixins (e.g. TimestampMixin, SoftDeleteMixin).
"""

from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import Boolean, Column, DateTime, String, cast, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

import uuid


def _parse_datetime(val):
    """Parse datetime from JSON-stored value (ISO string or None)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    return None


def _serialize_datetime(val):
    """Serialize datetime for JSON storage."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return val


# Keys stored in the attributes JSON column (service-specific models may extend)
USER_ATTRS_KEYS = frozenset(
    {
        "avatar_url",
        "first_name",
        "last_name",
        "provider",
        "confirmed_at",
        "verified",
        "verified_at",
        "service_account",
    }
)


class UserMixin:
    """Mixin providing shared user columns and hybrid properties.

    Use with SQLAlchemy declarative base and other mixins:

        class User(UserMixin, Base, TimestampMixin, SoftDeleteMixin):
            __tablename__ = "users"
            __table_args__ = (...)
            memberships = relationship("Membership", back_populates="user", ...)

    Provides:
        - id, email, external_id as regular columns
        - attributes JSONB column for avatar_url, first_name, last_name,
          provider, confirmed_at, verified, verified_at, service_account
        - hybrid_property accessors for query and instance use
        - full_name() helper
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=True)
    external_id = Column(String, nullable=True)
    attributes = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'")
    )

    def _get_attr(self, key, default=None):
        """Get value from attributes JSON."""
        return (self.attributes or {}).get(key, default)

    def _set_attr(self, key, value):
        """Set value in attributes JSON and mark modified."""
        if self.attributes is None:
            self.attributes = {}
        self.attributes[key] = value
        flag_modified(self, "attributes")

    @hybrid_property
    def avatar_url(self):
        return self._get_attr("avatar_url")

    @avatar_url.setter
    def avatar_url(self, value):
        self._set_attr("avatar_url", value)

    @avatar_url.expression
    def avatar_url(cls):
        return cls.attributes["avatar_url"].astext

    @hybrid_property
    def first_name(self):
        return self._get_attr("first_name", "")

    @first_name.setter
    def first_name(self, value):
        self._set_attr("first_name", value or "")

    @first_name.expression
    def first_name(cls):
        return cls.attributes["first_name"].astext

    @hybrid_property
    def last_name(self):
        return self._get_attr("last_name", "")

    @last_name.setter
    def last_name(self, value):
        self._set_attr("last_name", value or "")

    @last_name.expression
    def last_name(cls):
        return cls.attributes["last_name"].astext

    @hybrid_property
    def provider(self):
        return self._get_attr("provider")

    @provider.setter
    def provider(self, value):
        self._set_attr("provider", value)

    @provider.expression
    def provider(cls):
        return cls.attributes["provider"].astext

    @hybrid_property
    def confirmed_at(self):
        return _parse_datetime(self._get_attr("confirmed_at"))

    @confirmed_at.setter
    def confirmed_at(self, value):
        self._set_attr("confirmed_at", _serialize_datetime(value))

    @confirmed_at.expression
    def confirmed_at(cls):
        return cast(cls.attributes["confirmed_at"].astext, DateTime)

    @hybrid_property
    def verified(self):
        val = self._get_attr("verified")
        return bool(val) if val is not None else False

    @verified.setter
    def verified(self, value):
        self._set_attr("verified", bool(value) if value is not None else False)

    @verified.expression
    def verified(cls):
        return cast(cls.attributes["verified"].astext, Boolean)

    @hybrid_property
    def verified_at(self):
        return _parse_datetime(self._get_attr("verified_at"))

    @verified_at.setter
    def verified_at(self, value):
        self._set_attr("verified_at", _serialize_datetime(value))

    @verified_at.expression
    def verified_at(cls):
        return cast(cls.attributes["verified_at"].astext, DateTime)

    @hybrid_property
    def service_account(self):
        val = self._get_attr("service_account")
        return bool(val) if val is not None else False

    @service_account.setter
    def service_account(self, value):
        self._set_attr("service_account", bool(value) if value is not None else False)

    @service_account.expression
    def service_account(cls):
        return cast(cls.attributes["service_account"].astext, Boolean)

    def _build_user_attributes_from_kwargs(self, kwargs):
        """Build attributes dict from kwargs for __init__. Use in subclass __init__."""
        attrs = {}
        rest = {}
        for k, v in kwargs.items():
            if k in USER_ATTRS_KEYS:
                if k in ("confirmed_at", "verified_at") and isinstance(v, datetime):
                    attrs[k] = v.isoformat()
                elif k in ("verified", "service_account"):
                    attrs[k] = bool(v) if v is not None else False
                else:
                    attrs[k] = v
            else:
                rest[k] = v
        if attrs:
            rest["attributes"] = {**kwargs.get("attributes", {}), **attrs}
        return rest

    def full_name(self) -> str:
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}"
