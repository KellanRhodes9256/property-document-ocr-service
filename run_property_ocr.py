"""Explain the workflow by running one property PDF through it."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from document_triage import model_property_document
from property_document_service import ocr_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR and classify one scanned property document")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--lang", default="eng")
    parser.add_argument("--quality", default="accurate")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    pdf_bytes = args.pdf.read_bytes()
    text = await ocr_pdf(pdf_bytes, args.pdf.name, args.lang, args.quality)
    record = model_property_document(text)
    print(json.dumps(record.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
