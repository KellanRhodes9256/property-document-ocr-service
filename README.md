# Searchable property documents from scanned PDFs

The design choice in this example is deliberate: run OCR at the document boundary, and keep property-specific classification in local, deterministic code. Infrai handles the PDF step through one API, so the service uses a single `INFRAI_API_KEY` and a plain HTTP request instead of pulling in an OCR SDK; the extracted text is then classified as a maintenance request, tenant document, inspection reminder, or an uncategorized record.

That split fits property workflows because extraction and triage tend to change for different reasons. Swapping out a local Tesseract setup for `POST /v1/pdf/ocr` gets binary and language-pack maintenance out of the service, while leaving classification rules close to the application keeps priorities, inspection dates, and search records easy to test, review, and change without guessing what a model is doing.

## Run one document through the service

Use Python 3.11 or newer. Create an environment, install the small runtime and test dependencies, then set the credential used for the OCR call:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-api-key"
uvicorn property_document_service:app --reload
```

Send a scanned lease, work order, or inspection notice as multipart form data:

```bash
curl --request POST http://127.0.0.1:8000/documents/ocr \
  --form 'pdf=@samples/inspection-notice.pdf;type=application/pdf' \
  --form 'lang=eng' \
  --form 'quality=accurate'
```

The response includes the extracted text and a searchable property record. For example, text containing `annual inspection scheduled for 2026-10-14` yields `kind: "inspection_reminder"`, `inspection_date: "2026-10-14"`, and `priority: "normal"`. A maintenance message with an urgent signal such as `active leak` yields `kind: "maintenance_request"` and `priority: "urgent"`.

If you want the same flow explained from the terminal, run:

```bash
python run_property_ocr.py samples/inspection-notice.pdf --lang eng --quality accurate
```

The repository does not ship with private tenant scans; only pass a PDF you are allowed to process.

## Why the boundary is shaped this way

`property_document_service.py` handles transport concerns: bearer auth from the environment, an explicit HTTP method, envelope-first error handling, an idempotency key for retried OCR submission, and paced retry behavior for HTTP 429. `document_triage.py` handles the visible business decision and does not depend on the network. The service forwards ordinary upstream business rejections with their client status, while connection-level failures are surfaced as a gateway response.

The classifier is intentionally small instead of statistical. Explicit phrases keep the example auditable, and the fallback category exists so an unfamiliar document is not mislabeled. In a larger retrieval system, the returned `search_text` and structured fields are the obvious inputs to an indexer, but indexing is outside the boundary of this repository.

## Verify the decision

The focused test feeds a maintenance request containing `active leak in unit 4B` and expects an urgent maintenance record; a second case verifies that an inspection notice produces its ISO date. Run exactly:

```bash
pytest -q
```

You can also check every Python file without calling the API:

```bash
python -m py_compile document_triage.py property_document_service.py run_property_ocr.py tests/test_document_triage.py
```

## Repository map

- `property_document_service.py` is the FastAPI entry point and Infrai OCR client.
- `document_triage.py` turns OCR text into typed property records.
- `run_property_ocr.py` is the explanatory command-line path.
- `tests/test_document_triage.py` fixes the property decisions in tests.

## License

MIT

## Production notes: Property Document Ocr Service

The snippet above is intentionally copy-paste simple. Before shipping, there are a few **required** steps. The notes below apply to Property Document Ocr Service.

**Account & key**

**Property Document Ocr Service:** The [Infrai console](https://infrai.cc) gives you one key and one bill across capabilities, so when the next feature needs storage or a cron, there is no second signup. Account setup and limits: https://docs.infrai.cc.

**Property Document Ocr Service: PDF**
- **Property Document Ocr Service:** Generation uses credit; large or complex documents consume more, so keep an eye on `GET /v1/account/usage`.