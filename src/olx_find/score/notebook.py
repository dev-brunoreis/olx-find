"""Custo/benefício de notebook: pontos de hardware divididos pelo preço."""

from __future__ import annotations

import re

from olx_find.models import Ad

_GPU_POINTS = (
    (re.compile(r"RTX\s*40|RTX\s*50", re.I), 28),
    (re.compile(r"RTX\s*30", re.I), 22),
    (re.compile(r"RTX\s*20|GTX\s*16|RX\s*6", re.I), 16),
    (re.compile(r"GTX|RX\s*", re.I), 12),
    (re.compile(r"MX\s*", re.I), 6),
)


class NotebookValueScorer:
    def supports(self, specs: dict) -> bool:
        if specs.get("kind") != "notebook":
            return False
        return bool(specs.get("cpu") or specs.get("ram_gb") or specs.get("storage_gb") or specs.get("gpu"))

    def score(self, ad: Ad, specs: dict) -> float:
        if not ad.price or ad.price <= 0:
            return 0.0
        value = float(specs.get("cpu_points") or 0)
        ram = specs.get("ram_gb") or 0
        value += min(ram * 2, 64)
        storage = specs.get("storage_gb") or 0
        kind = specs.get("storage_kind")
        if storage and kind == "ssd":
            value += 18 + min(storage, 2048) / 64
        elif storage and kind == "hdd":
            value += 6 + min(storage, 2048) / 256
        elif storage:
            value += 8 + min(storage, 2048) / 128
        gpu = specs.get("gpu") or ""
        for pattern, points in _GPU_POINTS:
            if pattern.search(gpu):
                value += points
                break
        return round(value / ad.price * 1000, 2)
