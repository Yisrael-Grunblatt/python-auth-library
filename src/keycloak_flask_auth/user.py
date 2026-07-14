from __future__ import annotations

from typing import Any, Iterable


class User:
    def __init__(self, claims: dict[str, Any], client_id: str | None = None):
        self.claims = claims or {}
        self._client_id = client_id

    @property
    def sub(self) -> str | None:
        return self.claims.get("sub")

    @property
    def username(self) -> str | None:
        return self.claims.get("preferred_username")

    @property
    def email(self) -> str | None:
        return self.claims.get("email")

    @property
    def email_verified(self) -> bool:
        return bool(self.claims.get("email_verified", False))

    @property
    def name(self) -> str | None:
        return self.claims.get("name")

    @property
    def given_name(self) -> str | None:
        return self.claims.get("given_name")

    @property
    def family_name(self) -> str | None:
        return self.claims.get("family_name")

    @property
    def realm_roles(self) -> list[str]:
        return list(self.claims.get("realm_access", {}).get("roles", []))

    @property
    def client_roles(self) -> list[str]:
        if not self._client_id:
            return []
        resource = self.claims.get("resource_access", {})
        return list(resource.get(self._client_id, {}).get("roles", []))

    @property
    def roles(self) -> list[str]:
        return sorted(set(self.realm_roles) | set(self.client_roles))

    def has_role(self, *required: str) -> bool:
        owned = set(self.roles)
        return all(role in owned for role in required)

    def has_any_role(self, *required: str) -> bool:
        owned = set(self.roles)
        return any(role in owned for role in required)

    @classmethod
    def from_session(cls, data: dict[str, Any] | None, client_id: str | None = None) -> "User | None":
        if not data:
            return None
        return cls(data, client_id=client_id)

    def to_session(self) -> dict[str, Any]:
        return self.claims

    def __repr__(self) -> str:
        return f"<User username={self.username!r} roles={self.roles}>"

    def __contains__(self, role: str) -> bool:
        return role in self.roles

    def __iter__(self) -> Iterable[str]:
        return iter(self.roles)
