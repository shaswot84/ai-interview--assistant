"""Tests for the industry validation guardrail (Ollama classifier)."""

from unittest.mock import MagicMock, patch

import pytest

from industry_guardrail import validate_industry


def _mock_ollama(content: str) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


class TestValidateIndustry:
    """validate_industry calls Ollama and returns a boolean."""

    @patch("industry_guardrail.get_ollama_client")
    def test_valid_industry_returns_true(self, mock_get):
        mock_get().chat.completions.create.return_value = _mock_ollama(
            '{"is_valid": true}'
        )
        assert validate_industry("FinTech") is True

    @patch("industry_guardrail.get_ollama_client")
    def test_invalid_industry_returns_false(self, mock_get):
        mock_get().chat.completions.create.return_value = _mock_ollama(
            '{"is_valid": false}'
        )
        assert validate_industry("banana") is False

    @patch("industry_guardrail.get_ollama_client")
    def test_backend_engineer_returns_false(self, mock_get):
        mock_get().chat.completions.create.return_value = _mock_ollama(
            '{"is_valid": false}'
        )
        assert validate_industry("Backend Engineer") is False

    @patch("industry_guardrail.config")
    def test_missing_api_key_raises(self, mock_config):
        mock_config.ollama_api_key = ""
        with pytest.raises(RuntimeError, match="Ollama API key is not configured"):
            validate_industry("FinTech")

    @patch("industry_guardrail.get_ollama_client")
    def test_empty_response_raises(self, mock_get):
        mock_get().chat.completions.create.return_value = _mock_ollama(None)
        with pytest.raises(RuntimeError, match="Industry validation failed"):
            validate_industry("FinTech")

    @patch("industry_guardrail.get_ollama_client")
    def test_extra_text_around_json_fallback(self, mock_get):
        """Model returns extra explanatory text — regex fallback must still work."""
        mock_get().chat.completions.create.return_value = _mock_ollama(
            'I think this is valid. {"is_valid": true} Definitely an industry.'
        )
        assert validate_industry("Healthcare") is True

    @patch("industry_guardrail.get_ollama_client")
    def test_malformed_json_fallback(self, mock_get):
        """Model returns near-JSON with extra characters — regex fallback recovers."""
        mock_get().chat.completions.create.return_value = _mock_ollama(
            '{\n  "is_valid": false\n}\n```'
        )
        assert validate_industry("banana") is False
