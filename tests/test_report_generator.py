"""Unit tests for ReportGenerator."""

from pathlib import Path
import tempfile
import pytest

from core.config import ReportConfig
from reports.report_generator import ReportGenerator


def test_report_generation(tmp_path):
    agg_file = Path("data/processed/aggregation.json")
    if not agg_file.exists():
        pytest.skip("aggregation.json not generated yet")

    config = ReportConfig(
        template_path="reports/templates/report_template.md",
        output_format="markdown",
    )
    generator = ReportGenerator(config)

    out_file = tmp_path / "test_report.md"
    result = generator.generate(aggregation_path=agg_file, output_path=out_file)

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "# Google Photos AI-Powered Memory Retrieval Discovery Report" in content
    assert "Executive Summary" in content
    assert "Methodology & Data Provenance" in content
    assert "Cognitive Memory Model Analysis" in content
    assert "Opportunity Rankings & Prioritization Matrix" in content
