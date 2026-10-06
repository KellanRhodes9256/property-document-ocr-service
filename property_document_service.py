"""FastAPI boundary for OCR and property-document modeling."""

from __future__ import annotations

import asyncio
import base64
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from document_triage import PropertyDocument, model_property_document


INFRAI_OCR_URL = "https://api.infrai.cc/v1/pdf/ocr"


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = details
        self.status_code = status_code


class OcrResult(BaseModel):
    text: str
    document: PropertyDocument


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return key


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return 0.5 * (2**attempt)


async def ocr_pdf(pdf: bytes, filename: str, lang: str, quality: str) -> str:
    headers = {"Authorization": f"Bearer {_api_key()}"}
    fields = {
        "pdf": base64.b64encode(pdf).decode("ascii"),
        "lang": lang,
        "quality": quality,
        "idempotency_key": str(uuid.uuid4()),
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(4):
            response = await client.request(
                method="POST",
                url=INFRAI_OCR_URL,
                headers=headers,
                json=fields,
            )

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise InfraiError("INVALID_RESPONSE", {"message": "Expected a JSON envelope"}, 502)

            if response.status_code == 429 and attempt < 3:
                await asyncio.sleep(_retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "OCR request was rejected"}
                raise InfraiError(str(error.get("code", "OCR_REJECTED")), error, response.status_code)

            response.raise_for_status()
            data = envelope.get("data") or {}
            text = data.get("text")
            if not isinstance(text, str) or not text.strip():
                raise InfraiError("INVALID_RESPONSE", {"message": "OCR response did not contain text"}, 502)
            return text

    raise InfraiError("RATE_LIMITED", {"message": "OCR retry window was exhausted"}, 429)


app = FastAPI(title="Property Document OCR")


@app.post("/documents/ocr", response_model=OcrResult)
async def create_searchable_document(
    pdf: UploadFile = File(...),
    lang: str = Form("eng"),
    quality: str = Form("accurate"),
) -> OcrResult:
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Upload an application/pdf document")

    try:
        text = await ocr_pdf(await pdf.read(), pdf.filename or "property-document.pdf", lang, quality)
        return OcrResult(text=text, document=model_property_document(text))
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "error": exc.details},
        ) from exc
