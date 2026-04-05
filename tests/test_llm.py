import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas import LLMResult
from app.services.llm import LLMService, LLMServiceError, MAX_INPUT_CHARS, SYSTEM_PROMPT


class TestLLMServiceParseResponse:
    """Test the static _parse_response method (no API calls)."""

    def test_valid_json_response(self, mock_llm_response):
        result = LLMService._parse_response(json.dumps(mock_llm_response))
        assert result.category == "invoice"
        assert result.confidence == 0.95
        assert "Acme Corp" in result.summary
        assert result.extracted_data["vendor"] == "Acme Corp"
        assert len(result.flags) == 1

    def test_json_in_markdown_code_block(self, mock_llm_response):
        raw = f"```json\n{json.dumps(mock_llm_response)}\n```"
        result = LLMService._parse_response(raw)
        assert result.category == "invoice"
        assert result.confidence == 0.95

    def test_json_in_plain_code_block(self, mock_llm_response):
        raw = f"```\n{json.dumps(mock_llm_response)}\n```"
        result = LLMService._parse_response(raw)
        assert result.category == "invoice"

    def test_json_with_surrounding_text(self, mock_llm_response):
        raw = f"Here is the analysis:\n{json.dumps(mock_llm_response)}\nDone."
        result = LLMService._parse_response(raw)
        assert result.category == "invoice"

    def test_malformed_json(self):
        result = LLMService._parse_response("this is not json at all")
        assert result.category == "unknown"
        assert result.confidence == 0.0
        assert "not valid JSON" in result.flags[0]

    def test_partial_json(self):
        result = LLMService._parse_response('{"category": "invoice", "confidence": ')
        assert result.category == "unknown"

    def test_empty_response(self):
        result = LLMService._parse_response("")
        assert result.category == "unknown"

    def test_missing_fields_use_defaults(self):
        raw = json.dumps({"category": "contract"})
        result = LLMService._parse_response(raw)
        assert result.category == "contract"
        assert result.confidence == 0.0
        assert result.summary == ""
        assert result.extracted_data == {}

    def test_all_categories_parsed(self):
        categories = [
            "invoice", "contract", "report", "legal_brief",
            "financial_statement", "shipping_manifest", "unknown",
        ]
        for cat in categories:
            raw = json.dumps({"category": cat, "confidence": 0.9})
            result = LLMService._parse_response(raw)
            assert result.category == cat


class TestLLMServiceTruncation:
    def test_short_text_not_truncated(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            text = "Short document text"
            assert svc._truncate_text(text) == text

    def test_long_text_truncated(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            text = "x" * (MAX_INPUT_CHARS + 1000)
            truncated = svc._truncate_text(text)
            assert len(truncated) < len(text)
            assert "[... middle content omitted for length ...]" in truncated

    def test_truncation_preserves_start_and_end(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            start = "START_MARKER_" * 100
            end = "END_MARKER_" * 100
            middle = "m" * MAX_INPUT_CHARS
            text = start + middle + end
            truncated = svc._truncate_text(text)
            assert truncated.startswith("START_MARKER_")
            assert truncated.endswith("END_MARKER_")


class TestLLMServiceAnalyze:
    def test_empty_text_returns_unknown(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            result = svc.analyze_document("")
            assert result.category == "unknown"
            assert result.confidence == 0.0
            assert "no extractable text" in result.flags[0].lower()

    def test_whitespace_only_returns_unknown(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            result = svc.analyze_document("   \n\t  ")
            assert result.category == "unknown"

    @patch("app.services.llm.settings")
    def test_claude_provider_call(self, mock_settings, mock_llm_response):
        mock_settings.LLM_PROVIDER = "claude"
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            svc.provider = "claude"
            svc._claude_client = MagicMock()

            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=json.dumps(mock_llm_response))]
            svc._claude_client.messages.create.return_value = mock_message

            result = svc.analyze_document("Invoice text here")
            assert result.category == "invoice"
            svc._claude_client.messages.create.assert_called_once()

    @patch("app.services.llm.settings")
    def test_ollama_provider_call(self, mock_settings, mock_llm_response):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_MODEL = "mistral"

        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            svc.provider = "ollama"
            svc._ollama_client = MagicMock()

            svc._ollama_client.chat.return_value = {
                "message": {"content": json.dumps(mock_llm_response)}
            }

            result = svc.analyze_document("Invoice text here")
            assert result.category == "invoice"
            svc._ollama_client.chat.assert_called_once()

    def test_llm_call_failure_raises(self):
        with patch.object(LLMService, "__init__", lambda self: None):
            svc = LLMService()
            svc.provider = "claude"
            svc._claude_client = MagicMock()
            svc._claude_client.messages.create.side_effect = Exception("API down")

            # Disable retry for test
            with patch.object(svc, "_call_claude", side_effect=Exception("API down")):
                with pytest.raises(LLMServiceError, match="LLM call failed"):
                    svc.analyze_document("Some text")


class TestSystemPrompt:
    def test_prompt_contains_all_categories(self):
        for cat in ["invoice", "contract", "report", "legal_brief", "financial_statement", "shipping_manifest"]:
            assert cat in SYSTEM_PROMPT.lower()

    def test_prompt_requires_json_only(self):
        assert "ONLY valid JSON" in SYSTEM_PROMPT

    def test_prompt_contains_entity_types(self):
        for entity in ["people", "organizations", "dates", "monetary_amounts", "locations"]:
            assert entity in SYSTEM_PROMPT
