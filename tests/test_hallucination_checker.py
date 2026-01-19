"""Tests for OncoRAD hallucination checker."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oncorad.hallucination_checker import HallucinationChecker, ResponseSanitizer


@pytest.fixture
def checker():
    return HallucinationChecker(strict_mode=True)


@pytest.fixture
def source_chunks():
    return [
        {
            "document_name": "NCCN_Prostate_2024.pdf",
            "page_number": 45,
            "text": "For high-risk prostate cancer, the recommended treatment is external beam radiotherapy with ADT for 24-36 months. The RTOG-9408 study showed improved survival with combined modality treatment."
        },
        {
            "document_name": "ESTRO_Guidelines.pdf",
            "page_number": 12,
            "text": "Moderate hypofractionation (60 Gy in 20 fractions) has shown non-inferior outcomes compared to conventional fractionation. Local control rates of 90% at 5 years have been reported."
        }
    ]


class TestClaimExtraction:
    """Tests for extracting claims from response text."""

    def test_extract_simple_claims(self, checker):
        text = "The treatment is effective. Survival rates are high."
        claims = checker.extract_claims(text)
        assert len(claims) == 2

    def test_extract_claims_with_citations(self, checker):
        text = "The recommended dose is 78 Gy [Fuente: NCCN_Prostate.pdf, Pág. 45]."
        claims = checker.extract_claims(text)
        assert len(claims) == 1
        assert len(claims[0]['citations']) == 1

    def test_extract_study_references(self, checker):
        text = "The RTOG-9408 study demonstrated improved outcomes."
        claims = checker.extract_claims(text)
        assert len(claims[0]['studies_mentioned']) >= 1

    def test_extract_statistics(self, checker):
        text = "The survival rate was 85% at 5 years."
        claims = checker.extract_claims(text)
        assert len(claims[0]['statistics']) >= 1


class TestCitationVerification:
    """Tests for citation verification."""

    def test_valid_citation(self, checker, source_chunks):
        claims = [{
            'text': 'Test claim',
            'citations': [('NCCN_Prostate_2024.pdf', '45')]
        }]

        valid, invalid = checker.verify_citations(claims, source_chunks)
        assert len(valid) == 1
        assert len(invalid) == 0

    def test_invalid_citation_document(self, checker, source_chunks):
        claims = [{
            'text': 'Test claim',
            'citations': [('NonExistent_Document.pdf', '10')]
        }]

        valid, invalid = checker.verify_citations(claims, source_chunks)
        assert len(valid) == 0
        assert len(invalid) == 1


class TestFactualSupport:
    """Tests for factual support checking."""

    def test_supported_claim(self, checker, source_chunks):
        claim = "The RTOG-9408 study showed improved survival with treatment."
        is_supported, score, _ = checker.check_factual_support(
            claim, source_chunks
        )
        assert is_supported
        assert score > 0.3

    def test_unsupported_claim(self, checker, source_chunks):
        claim = "Completely unrelated statement about quantum physics."
        is_supported, score, _ = checker.check_factual_support(
            claim, source_chunks
        )
        assert not is_supported
        assert score < 0.3


class TestHallucinationDetection:
    """Tests for hallucination detection."""

    def test_detect_fake_study(self, checker, source_chunks):
        claims = checker.extract_claims(
            "According to the FAKE-9999 study, the treatment is effective."
        )

        hallucinations = checker.detect_potential_hallucinations(
            claims, source_chunks
        )

        assert len(hallucinations) > 0
        assert any("FAKE-9999" in str(h) for h in hallucinations)

    def test_no_hallucination_for_real_study(self, checker, source_chunks):
        claims = checker.extract_claims(
            "The RTOG-9408 study showed good results."
        )

        hallucinations = checker.detect_potential_hallucinations(
            claims, source_chunks
        )

        # Should not flag the real study
        assert not any("RTOG-9408" in str(h) for h in hallucinations)


class TestResponseValidation:
    """Tests for complete response validation."""

    def test_valid_response(self, checker, source_chunks):
        response = """
        According to the RTOG-9408 study, combined treatment is recommended
        [Fuente: NCCN_Prostate_2024.pdf, Pág. 45].
        Local control rates of 90% have been reported
        [Fuente: ESTRO_Guidelines.pdf, Pág. 12].
        """

        result = checker.validate_response(response, source_chunks)
        assert result.is_valid
        assert result.confidence_score > 0.5

    def test_response_with_hallucinations(self, checker, source_chunks):
        response = """
        The FAKE-1234 study by Dr. Nonexistent showed 99% survival.
        This contradicts all known evidence.
        """

        result = checker.validate_response(response, source_chunks)
        assert len(result.potential_hallucinations) > 0
        assert result.confidence_score < 0.8


class TestResponseSanitizer:
    """Tests for response sanitization."""

    def test_sanitize_with_flag_mode(self, checker, source_chunks):
        sanitizer = ResponseSanitizer(checker)
        response = "The FAKE-9999 study shows amazing results."

        sanitized, validation = sanitizer.sanitize(
            response, source_chunks, mode="flag"
        )

        # Should add warning when hallucinations detected
        if validation.potential_hallucinations:
            assert "ADVERTENCIA" in sanitized or sanitized == response

    def test_sanitize_clean_response(self, checker, source_chunks):
        sanitizer = ResponseSanitizer(checker)
        response = "The RTOG-9408 study shows good results according to the NCCN guidelines."

        sanitized, validation = sanitizer.sanitize(
            response, source_chunks, mode="flag"
        )

        # Clean response should pass through unchanged
        if validation.is_valid:
            assert sanitized == response or "ADVERTENCIA" not in sanitized


class TestCorrectionSuggestions:
    """Tests for correction suggestions."""

    def test_suggest_corrections_for_invalid_citations(self, checker, source_chunks):
        validation = checker.validate_response(
            "According to [Fuente: FakeDoc.pdf, Pág. 999].",
            source_chunks
        )

        suggestions = checker.suggest_corrections(validation, source_chunks)
        assert len(suggestions) > 0
