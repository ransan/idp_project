import json
import re

import anthropic
import groq
import ollama as ollama_client
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.schemas import LLMResult

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an expert document analyst for professional services.
Given raw document text, return ONLY valid JSON (no markdown, no explanation) with this exact structure:

{
  "category": "<invoice|contract|report|legal_brief|financial_statement|shipping_manifest|unknown>",
  "confidence": <float 0.0-1.0>,
  "summary": "<2-4 sentence summary>",
  "extracted_data": {<structured fields per document type>},
  "key_entities": {
    "people": [],
    "organizations": [],
    "dates": [],
    "monetary_amounts": [],
    "locations": [],
    "reference_numbers": []
  },
  "flags": ["<any anomalies, risks, deadlines within 30 days, missing info, compliance concerns>"]
}

EXTRACTION RULES PER CATEGORY:
- Invoice: vendor, buyer, invoice_number, date, due_date, line_items (description, quantity, unit_price, total), total_amount, currency, payment_terms
- Contract: parties, effective_date, expiration_date, contract_type, governing_law, key_clauses, termination_conditions
- Report: title, author, date, key_findings, recommendations
- Legal Brief: case_name, court, parties, key_arguments, relief_sought
- Financial Statement: entity, period, revenue, expenses, net_income, key_figures, auditor
- Shipping Manifest: shipper, consignee, origin, destination, items (description, quantity, weight), tracking_numbers

Return ONLY the JSON object. No other text."""

MAX_INPUT_CHARS = 100_000  # ~25k tokens


class LLMServiceError(Exception):
    pass


class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        if self.provider == "claude":
            self._claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "groq":
            self._groq_client = groq.Groq(api_key=settings.GROQ_API_KEY)
        elif self.provider == "ollama":
            self._ollama_client = ollama_client.Client(host=settings.OLLAMA_BASE_URL)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.APITimeoutError, anthropic.RateLimitError)),
        reraise=True,
    )
    def _call_claude(self, text: str) -> str:
        message = self._claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Analyze this document:\n\n{text}"}],
        )
        return message.content[0].text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((groq.APITimeoutError, groq.RateLimitError)),
        reraise=True,
    )
    def _call_groq(self, text: str) -> str:
        response = self._groq_client.chat.completions.create(
            model=settings.GROQ_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this document:\n\n{text}"},
            ],
        )
        return response.choices[0].message.content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _call_ollama(self, text: str) -> str:
        response = self._ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this document:\n\n{text}"},
            ],
        )
        return response["message"]["content"]

    def analyze_document(self, text: str) -> LLMResult:
        if not text or not text.strip():
            return LLMResult(
                category="unknown",
                confidence=0.0,
                summary="Empty document — no text content to analyze.",
                flags=["Document contains no extractable text"],
            )

        truncated_text = self._truncate_text(text)

        try:
            if self.provider == "claude":
                raw = self._call_claude(truncated_text)
            elif self.provider == "groq":
                raw = self._call_groq(truncated_text)
            else:
                raw = self._call_ollama(truncated_text)
        except Exception as e:
            logger.error("llm_call_failed", provider=self.provider, error=str(e))
            raise LLMServiceError(f"LLM call failed: {e}") from e

        return self._parse_response(raw)

    def _truncate_text(self, text: str) -> str:
        if len(text) <= MAX_INPUT_CHARS:
            return text
        half = MAX_INPUT_CHARS // 2
        return (
            text[:half]
            + "\n\n[... middle content omitted for length ...]\n\n"
            + text[-half:]
        )

    @staticmethod
    def _parse_response(raw: str) -> LLMResult:
        # Try to extract JSON from the response (handle markdown code blocks)
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        # Try direct JSON parse
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            # Try to find a JSON object in the response
            brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if brace_match:
                try:
                    data = json.loads(brace_match.group())
                except json.JSONDecodeError:
                    logger.warning("llm_json_parse_failed", raw_response=raw[:500])
                    return LLMResult(
                        category="unknown",
                        confidence=0.0,
                        summary="Failed to parse LLM response.",
                        flags=["LLM response was not valid JSON"],
                    )
            else:
                logger.warning("llm_no_json_found", raw_response=raw[:500])
                return LLMResult(
                    category="unknown",
                    confidence=0.0,
                    summary="Failed to parse LLM response.",
                    flags=["LLM response was not valid JSON"],
                )

        return LLMResult(
            category=data.get("category", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            summary=data.get("summary", ""),
            extracted_data=data.get("extracted_data", {}),
            key_entities=data.get("key_entities", {}),
            flags=data.get("flags", []),
        )
