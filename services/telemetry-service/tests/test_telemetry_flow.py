"""Tests for telemetry-service.

TODO: no automated tests written yet — all verification so far has been
manual (curl) testing of the full auth/ingestion/mapping flow. Needs a
conftest.py with fixtures mirroring asset-service's pattern (mocked
verify_ingestion_key / check_facility_role, real signed JWTs via
jose.jwt.encode for auth_headers) before this is genuinely tested.
"""
