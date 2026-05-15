"""Verify benchmark documentation exists (P2)."""
import pathlib


def test_bench_results_txt_exists():
    """formal/bench_results.txt must exist and be non-empty."""
    path = pathlib.Path("formal/bench_results.txt")
    assert path.exists(), "formal/bench_results.txt does not exist"
    assert path.stat().st_size > 0, "formal/bench_results.txt is empty"
