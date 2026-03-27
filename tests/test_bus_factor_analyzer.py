from __future__ import annotations

from techwill.analyzers.bus_factor import BusFactorAnalyzer


def test_bus_factor_groups_exclusive_files_by_top_module() -> None:
    exclusive_files = [
        "src/payments/core.py",
        "src/payments/retry.py",
        "infra/deploy/main.tf",
        "README.md",
    ]

    modules = BusFactorAnalyzer(min_files_per_module=1).analyze(exclusive_files=exclusive_files)

    assert modules == [".", "infra", "src"]

