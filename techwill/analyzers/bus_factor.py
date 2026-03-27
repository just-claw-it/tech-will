from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath


class BusFactorAnalyzer:
    """Infer module-level bus factor risk from exclusive files."""

    def __init__(self, *, min_files_per_module: int = 1) -> None:
        self.min_files_per_module = min_files_per_module

    def analyze(self, *, exclusive_files: list[str]) -> list[str]:
        if not exclusive_files:
            return []

        modules: Counter[str] = Counter()
        for file_path in exclusive_files:
            modules[self._module_for_file(file_path)] += 1

        bus_factor_modules = [
            module for module, count in modules.items() if count >= self.min_files_per_module
        ]
        return sorted(bus_factor_modules)

    @staticmethod
    def _module_for_file(file_path: str) -> str:
        path = PurePosixPath(file_path)
        if len(path.parts) <= 1:
            return "."
        # Use top-level directory as a lightweight module boundary in v1.
        return path.parts[0]

