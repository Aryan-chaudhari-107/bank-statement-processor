"""Unit and integration tests for the statement processing pipeline."""

from pathlib import Path

from src.pipeline import process_statement

SAMPLE_DIR = Path("sample_data")


def test_pipeline_text_statement() -> None:
    """Test process_statement on a clean text statement producing structured output and no warnings."""
    pdf_path = SAMPLE_DIR / "text_bordered.pdf"
    result = process_statement(pdf_path)

    assert result["page_types"] == ["text", "text"]
    assert "account_holder" in result["account_details"]
    assert len(result["transactions"]) == 28
    assert result["summary"]["total_rows"] == 28
    assert result["summary"]["flagged_rows"] == 0
    assert result["warnings"] == []
