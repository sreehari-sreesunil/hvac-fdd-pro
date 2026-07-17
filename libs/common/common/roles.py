"""Shared RBAC role definitions, used across all services."""

import enum


class Role(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"
