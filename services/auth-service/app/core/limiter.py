"""Shared slowapi Limiter instance.

Kept in its own module, not defined directly in main.py, to avoid a
circular import: main.py needs to import auth.py's router, and auth.py
needs to import this same limiter to decorate its endpoints - both
importing from a third, dependency-free module breaks that cycle.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
