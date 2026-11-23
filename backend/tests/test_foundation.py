from fastapi.testclient import TestClient

import app.modules
from app.core.database import Base
from app.core.ids import new_uuid7
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.main import app


def test_liveness_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Finance4Dummies"


def test_uuid7_version_and_ordering() -> None:
    first = new_uuid7()
    second = new_uuid7()
    assert first.version == 7
    assert second.version == 7
    assert first != second


def test_password_and_token_roundtrip() -> None:
    hashed = hash_password("S3cureP@ssword!")
    assert verify_password("S3cureP@ssword!", hashed)
    assert not verify_password("wrong-password", hashed)

    subject = new_uuid7()
    token = create_access_token(subject)
    claims = decode_access_token(token)
    assert claims["sub"] == str(subject)
    assert claims["type"] == "access"

    raw_refresh, digest = generate_refresh_token()
    assert hash_refresh_token(raw_refresh) == digest


def test_all_domain_tables_registered() -> None:
    expected_tables = {
        "users",
        "refresh_tokens",
        "institutions",
        "accounts",
        "categories",
        "recurring_rules",
        "recurring_occurrences",
        "cash_transactions",
        "instruments",
        "instrument_provider_symbols",
        "bond_details",
        "pac_plans",
        "pac_executions",
        "portfolio_transactions",
        "market_prices",
        "fx_rates",
        "portfolio_daily_snapshots",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))
