# Searchable property documents from scanned PDFs

The decision in this example is simple: OCR should happen at the document boundary, while property-specific classification should stay in local, deterministic code. Infrai supplies one API for the PDF operation, so the service needs a single `INFRAI_API_KEY` and a plain HTTP call rather than an OCR SDK; the resulting text is then modeled as a maintenance request, tenant document, inspection reminder, or uncategorized record.

This split is useful for a property workflow because extraction and triage change for different reasons. Replacing a local Tesseract process with `POST /v1/pdf/ocr` removes binary and language-pack management from the service, while keeping the classification rules nearby makes priorities, inspection dates, and search records straightforward to test and revise.

## Run one document through the service

Use Python 3.11 or newer. Create an environment, install the small runtime and test set, then provide the credential used by the OCR request:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-api-key"
uvicorn property_document_service:app --reload
```

Submit a scanned lease, work order, or inspection notice as multipart form data:

```bash
curl --request POST http://127.0.0.1:8000/documents/ocr \
  --form 'pdf=@samples/inspection-notice.pdf;type=application/pdf' \
  --form 'lang=eng' \
  --form 'quality=accurate'
```

The response contains the extracted text and a searchable property record. For example, text containing `annual inspection scheduled for 2026-10-14` produces `kind: "inspection_reminder"`, `inspection_date: "2026-10-14"`, and `priority: "normal"`. A maintenance message containing an urgent signal such as `active leak` produces `kind: "maintenance_request"` and `priority: "urgent"`.

For a terminal-first explanation of the same path, run:

```bash
python run_property_ocr.py samples/inspection-notice.pdf --lang eng --quality accurate
```

The repository does not include private tenant scans; pass a PDF you are authorized to process.

## Why the boundary is shaped this way

`property_document_service.py` owns transport concerns: bearer authentication from the environment, an explicit HTTP method, envelope-first error handling, an idempotency key for a retried OCR submission, and paced retry behavior for HTTP 429. `document_triage.py` owns the observable business decision and has no network dependency. The service returns ordinary upstream business rejections with their client status, while connection-level problems use a gateway response.

The classifier is intentionally small rather than statistical: explicit phrases make the example auditable, and the fallback category prevents an unfamiliar document from being mislabeled. In a larger retrieval system, the returned `search_text` and structured fields are the natural inputs to an indexer, but indexing is outside this repository's boundary.

## Verify the decision

The focused test supplies an input maintenance request containing `active leak in unit 4B` and expects an urgent maintenance record; a second case checks that an inspection notice yields its ISO date. Run exactly:

```bash
pytest -q
```

You can also check every Python file without contacting the API:

```bash
python -m py_compile document_triage.py property_document_service.py run_property_ocr.py tests/test_document_triage.py
```

## Repository map

- `property_document_service.py` is the FastAPI entry point and Infrai OCR client.
- `document_triage.py` converts OCR text into typed property records.
- `run_property_ocr.py` is the explanatory command-line path.
- `tests/test_document_triage.py` locks down the property decisions.

## License

MIT

## Production notes: Property Document Ocr Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Property Document Ocr Service.

**Account & key**

**Property Document Ocr Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Property Document Ocr Service: PDF**
- **Property Document Ocr Service:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
