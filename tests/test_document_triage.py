from datetime import date
import asyncio
import base64
import json

import httpx

from property_document_service import ocr_pdf

from document_triage import DocumentKind, Priority, model_property_document


def test_active_leak_becomes_an_urgent_maintenance_request() -> None:
    record = model_property_document("  Tenant reports an active leak in unit 4B.  ")

    assert record.kind is DocumentKind.MAINTENANCE_REQUEST
    assert record.priority is Priority.URGENT
    assert record.search_text == "Tenant reports an active leak in unit 4B."


def test_inspection_notice_exposes_its_date() -> None:
    record = model_property_document("Annual inspection scheduled for 2026-10-14")

    assert record.kind is DocumentKind.INSPECTION_REMINDER
    assert record.priority is Priority.NORMAL
    assert record.inspection_date == date(2026, 10, 14)


def test_ocr_sends_json_fields(monkeypatch) -> None:
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "application/json"
        assert request.headers["authorization"] == "Bearer test-key"
        fields = json.loads(request.content)
        assert set(fields) == {"pdf", "lang", "quality", "idempotency_key"}
        assert base64.b64decode(fields["pdf"]) == b"%PDF-test"
        assert fields["lang"] == "eng"
        assert fields["quality"] == "accurate"
        return httpx.Response(200, json={"ok": True, "data": {"text": "Inspection scheduled"}})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    assert asyncio.run(ocr_pdf(b"%PDF-test", "test.pdf", "eng", "accurate")) == "Inspection scheduled"
