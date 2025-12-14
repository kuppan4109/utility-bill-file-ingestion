"""
OpenAI text-based extractor for utility bills (PDF -> text -> JSON)

- Uses Chat Completions JSON mode (no Responses API)
- Extracts PDF text locally (pdfplumber -> PyPDF2 fallback)
- Returns SAME schema as pdfco.py::parse_bill_text

Env:
  OPENAI_API_KEY (required)
  OPENAI_ORG (optional)
  OPENAI_CHAT_MODEL (optional, default: gpt-4o-mini)

Deps:
  openai>=1.13,<2
  pdfplumber>=0.11.0
  PyPDF2>=3.0.0
"""

from __future__ import annotations
import io
import os
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "You are a strict JSON extractor for utility bills. "
    "Return only valid JSON (no extra commentary). "
    "Numbers must be plain (no $ or commas). "
    "Dates must be YYYY-MM-DD or null when unknown. "
    "Include all requested keys even if the value is null."
)

USER_INSTRUCTIONS = """
Extract the following fields from the bill text. Return only valid JSON in this exact schema:

{
  "provider_name": string or null,
  "utility_type": "gas" | "water" | "electricity" | "trash" | "sewer" | "other" | null,
  "customer_name": string or null,
  "account_number": string or null,
  "service_address": string or null,
  "mailing_address": string or null,
  "invoice_id": string or null,
  "issue_id": string or null,
  "statement_issued": YYYY-MM-DD or null,
  "service_start": YYYY-MM-DD or null,
  "service_end": YYYY-MM-DD or null,
  "amount_due_by": YYYY-MM-DD or null,
  "due_date": YYYY-MM-DD or null,
  "amount_due_after": YYYY-MM-DD or null,
  "previous_balance": number or null,
  "payments": number or null,
  "balance_forward": number or null,
  "past_due_balance": number or null,
  "current_charges": number or null,
  "water_charges": number or null,
  "sewer_charges": number or null,
  "storm_water_charges": number or null,
  "environmental_fee": number or null,
  "trash_charges": number or null,
  "gas_charges": number or null,
  "electric_charges": number or null,
  "total_amount_due": number or null,
  "rate_plan": string or null,
  "service_days": number or null,
  "total_usage": number or null,
  "meters": [
    {
      "meter_number": string or null,
      "previous_read": string or null,
      "usage": number or null,
      "base_charge": number or null,
      "usage_charge": number or null,
      "total": number or null
    }
  ] or null
}

Rules:
- Dates as YYYY-MM-DD or null.
- Numbers must be plain (no $ or commas).
- If field not found, set it to null.
- 'utility_type' can be inferred from provider/charges (gas, water, electricity, trash, sewer, other).
- Include all keys even if null.
"""

def _pdf_to_text(pdf_bytes: bytes) -> str:
    """pdfplumber first, then PyPDF2 fallback."""
    try:
        import pdfplumber  # type: ignore
        pages: List[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
        txt = "\n".join(pages).strip()
        if txt:
            return txt
        logger.warning("pdfplumber returned empty; falling back to PyPDF2")
    except Exception as e:
        logger.warning("pdfplumber failed (%s); falling back to PyPDF2", e)

    try:
        from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(pdf_bytes))
        txt = "\n".join([(p.extract_text() or "") for p in reader.pages]).strip()
        if not txt:
            raise RuntimeError("Empty text after PyPDF2")
        return txt
    except Exception as e:
        logger.error("PyPDF2 failed: %s", e)
        raise RuntimeError("Unable to read PDF text") from e

class OpenAIExtractor:
    """OpenAI Chat JSON-mode extractor producing pdfco-compatible schema."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, org: Optional[str] = None):
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=key, organization=org or os.getenv("OPENAI_ORG"))
        self.model = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    def extract(self, pdf_content: bytes) -> Dict[str, Any]:
        bill_text = _pdf_to_text(pdf_content)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": (
                            USER_INSTRUCTIONS
                            + "\n\n=== BILL TEXT START ===\n"
                            + bill_text[:150000]
                            + "\n=== BILL TEXT END ==="
                        ),
                    },
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e, exc_info=True)
            raise

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("Model returned empty content")

        try:
            parsed = json.loads(content)
        except Exception as e:
            logger.error("Invalid JSON from model: %s; raw=%s", e, content[:800])
            raise RuntimeError("Model did not return valid JSON") from e

        # Additive post-processing: telecom provider hint
        try:
            pn = (parsed.get("provider_name") or "").strip().lower()
            if pn.startswith("comcast"):
                parsed["utility_type"] = parsed.get("utility_type") or "other"
        except Exception:
            pass

        return {
            "provider_name": parsed.get("provider_name"),
            "utility_type": parsed.get("utility_type"),
            "customer_name": parsed.get("customer_name"),
            "account_number": parsed.get("account_number"),
            "service_address": parsed.get("service_address"),
            "mailing_address": parsed.get("mailing_address"),
            "invoice_id": parsed.get("invoice_id"),
            "issue_id": parsed.get("issue_id"),
            "statement_issued": parsed.get("statement_issued"),
            "service_start": parsed.get("service_start"),
            "service_end": parsed.get("service_end"),
            "amount_due_by": parsed.get("amount_due_by"),
            "due_date": parsed.get("due_date"),
            "amount_due_after": parsed.get("amount_due_after"),
            "previous_balance": parsed.get("previous_balance"),
            "payments": parsed.get("payments"),
            "balance_forward": parsed.get("balance_forward"),
            "past_due_balance": parsed.get("past_due_balance"),
            "current_charges": parsed.get("current_charges"),
            "water_charges": parsed.get("water_charges"),
            "sewer_charges": parsed.get("sewer_charges"),
            "storm_water_charges": parsed.get("storm_water_charges"),
            "environmental_fee": parsed.get("environmental_fee"),
            "trash_charges": parsed.get("trash_charges"),
            "gas_charges": parsed.get("gas_charges"),
            "electric_charges": parsed.get("electric_charges"),
            "total_amount_due": parsed.get("total_amount_due"),
            "rate_plan": parsed.get("rate_plan"),
            "service_days": parsed.get("service_days"),
            "total_usage": parsed.get("total_usage"),
            "meters": self._normalize_meters(parsed.get("meters")),
            "confidence": 0.80,
            "raw_text_sample": bill_text[:2000],
        }

    @staticmethod
    def _normalize_meters(meters_val: Any) -> Optional[List[Dict[str, Any]]]:
        if meters_val is None:
            return None
        try:
            if isinstance(meters_val, list):
                out: List[Dict[str, Any]] = []
                for m in meters_val:
                    if not isinstance(m, dict):
                        continue
                    out.append({
                        "meter_number": m.get("meter_number"),
                        "previous_read": m.get("previous_read"),
                        "usage": m.get("usage"),
                        "base_charge": m.get("base_charge"),
                        "usage_charge": m.get("usage_charge"),
                        "total": m.get("total"),
                    })
                return out or None
            if isinstance(meters_val, dict):
                m = meters_val
                return [{
                    "meter_number": m.get("meter_number"),
                    "previous_read": m.get("previous_read"),
                    "usage": m.get("usage"),
                    "base_charge": m.get("base_charge"),
                    "usage_charge": m.get("usage_charge"),
                    "total": m.get("total"),
                }]
        except Exception as e:
            logger.warning("meters normalization failed: %s", e)
        return None
