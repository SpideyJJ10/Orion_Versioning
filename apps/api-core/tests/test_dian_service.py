from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_dian_disabled_provider_keeps_invoice_pending(monkeypatch):
    from backend.services.dian import _emit

    monkeypatch.delenv("DIAN_PROVIDER", raising=False)
    orden = SimpleNamespace()

    result = await _emit(orden)

    assert result.status == "pending"
    assert "no configurado" in result.error


@pytest.mark.asyncio
async def test_dian_mock_provider_is_blocked_in_production(monkeypatch):
    from backend.services.dian import _emit

    monkeypatch.setenv("DIAN_PROVIDER", "mock")
    monkeypatch.setenv("ENV", "production")
    orden = SimpleNamespace()

    result = await _emit(orden)

    assert result.status == "failed"
    assert "produccion" in result.error
