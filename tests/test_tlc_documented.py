"""Verify TLC documentation exists (P2)."""
import pathlib


def test_tlc_results_md_exists():
    """formal/tlc_results.md must exist and be non-empty."""
    path = pathlib.Path("formal/tlc_results.md")
    assert path.exists(), "formal/tlc_results.md does not exist"
    assert path.stat().st_size > 0, "formal/tlc_results.md is empty"
