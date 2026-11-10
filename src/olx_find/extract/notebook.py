"""Extrai CPU, RAM, armazenamento e GPU de anúncios de notebook."""

from __future__ import annotations

import re

from olx_find.models import Ad

_NOTEBOOK = re.compile(r"\b(notebooks?|laptops?|netbooks?)\b", re.I)

_CPU_PATTERNS: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(r"\b(?:apple\s*)?m4(?:\s*(?:pro|max))?\b", re.I), "Apple M4", 95),
    (re.compile(r"\b(?:apple\s*)?m3(?:\s*(?:pro|max))?\b", re.I), "Apple M3", 85),
    (re.compile(r"\b(?:core\s*)?ultra\s*9\b|\bi9\b", re.I), "i9 / Ultra 9", 90),
    (re.compile(r"\bryzen\s*9\b", re.I), "Ryzen 9", 90),
    (re.compile(r"\b(?:apple\s*)?m2(?:\s*(?:pro|max))?\b", re.I), "Apple M2", 70),
    (re.compile(r"\b(?:core\s*)?ultra\s*7\b|\bi7\b", re.I), "i7 / Ultra 7", 70),
    (re.compile(r"\bryzen\s*7\b", re.I), "Ryzen 7", 70),
    (re.compile(r"\b(?:apple\s*)?m1(?:\s*(?:pro|max))?\b", re.I), "Apple M1", 55),
    (re.compile(r"\b(?:core\s*)?ultra\s*5\b|\bi5\b", re.I), "i5 / Ultra 5", 50),
    (re.compile(r"\bryzen\s*5\b", re.I), "Ryzen 5", 50),
    (re.compile(r"\b(?:core\s*)?i3\b", re.I), "i3", 30),
    (re.compile(r"\bryzen\s*3\b", re.I), "Ryzen 3", 30),
    (re.compile(r"\b(?:celeron|pentium|athlon)\b", re.I), "entrada", 12),
]

_CAPACITY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(tb|gb)\b", re.I)
_SSD = re.compile(r"\b(ssd|nvme|m\.2)\b", re.I)
_HDD = re.compile(r"\b(hdd|hd)\b", re.I)
_RAM_WORD = re.compile(r"\b(ram|mem[oó]ria|ddr\d?)\b", re.I)
_RAM_SIZES = {4, 8, 12, 16, 18, 20, 24, 32, 36, 48, 64, 96, 128}

_GPU = re.compile(
    r"\b(rtx\s*\d{3,4}(?:\s*ti)?|gtx\s*\d{3,4}(?:\s*ti)?|rx\s*\d{3,4}|mx\s*\d{3})\b",
    re.I,
)


class NotebookSpecExtractor:
    def supports(self, query: str, ad: Ad) -> bool:
        blob = f"{query} {ad.title} {ad.text()}"
        return bool(_NOTEBOOK.search(blob))

    def extract(self, ad: Ad) -> dict:
        text = ad.text()
        cpu_label, cpu_points = _cpu(text)
        ram_gb = _ram(text)
        storage_gb, storage_kind = _storage(text)
        gpu = _gpu(text)
        specs = {
            "kind": "notebook",
            "cpu": cpu_label,
            "cpu_points": cpu_points,
            "ram_gb": ram_gb,
            "storage_gb": storage_gb,
            "storage_kind": storage_kind,
            "gpu": gpu,
        }
        specs["summary"] = _summary(specs)
        return specs


def _cpu(text: str) -> tuple[str | None, int]:
    best_label = None
    best_points = 0
    for pattern, label, points in _CPU_PATTERNS:
        if pattern.search(text) and points > best_points:
            best_label = label
            best_points = points
    return best_label, best_points


def _ram(text: str) -> int | None:
    for cap in _capacities(text):
        if cap["role"] == "ram":
            return cap["gb"]
    return None


def _storage(text: str) -> tuple[int | None, str | None]:
    disks = [cap for cap in _capacities(text) if cap["role"] == "storage"]
    if not disks:
        kind = "ssd" if _SSD.search(text) else "hdd" if _HDD.search(text) else None
        return None, kind
    best = max(disks, key=lambda cap: cap["gb"])
    return best["gb"], best["kind"] or "storage"


def _capacities(text: str) -> list[dict]:
    """Cada GB/TB vira RAM ou armazenamento. Cada rótulo (ssd, hd, ram) cola no número mais próximo."""
    raw = []
    for match in _CAPACITY.finditer(text):
        raw.append({
            "at": match.start(),
            "gb": _to_gb(match.group(1), match.group(2)),
            "unit": match.group(2).lower(),
            "label": None,
        })
    labels = [(m.start(), "ssd") for m in _SSD.finditer(text)]
    labels += [(m.start(), "hdd") for m in _HDD.finditer(text)]
    labels += [(m.start(), "ram") for m in _RAM_WORD.finditer(text)]
    pairs = []
    for label_index, (pos, kind) in enumerate(labels):
        for cap_index, cap in enumerate(raw):
            distance = abs(pos - cap["at"])
            if distance > 24:
                continue
            follows = 0 if cap["at"] >= pos else 1
            pairs.append((distance, follows, label_index, cap_index, kind))
    pairs.sort()
    used_labels: set[int] = set()
    used_caps: set[int] = set()
    for _distance, _follows, label_index, cap_index, kind in pairs:
        if label_index in used_labels or cap_index in used_caps:
            continue
        raw[cap_index]["label"] = kind
        used_labels.add(label_index)
        used_caps.add(cap_index)

    caps = []
    for cap in raw:
        kind = cap["label"]
        if kind in {"ssd", "hdd"} or cap["unit"] == "tb" or cap["gb"] >= 192:
            caps.append({"gb": cap["gb"], "role": "storage", "kind": kind if kind in {"ssd", "hdd"} else None})
        elif kind == "ram" or cap["gb"] in _RAM_SIZES:
            caps.append({"gb": cap["gb"], "role": "ram", "kind": None})
    return caps


def _to_gb(amount: str, unit: str) -> int:
    value = float(amount.replace(",", "."))
    if unit.lower() == "tb":
        value *= 1024
    return int(value)


def _gpu(text: str) -> str | None:
    match = _GPU.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).upper()


def _summary(specs: dict) -> str:
    parts = []
    if specs.get("cpu"):
        parts.append(specs["cpu"])
    if specs.get("ram_gb"):
        parts.append(f"{specs['ram_gb']}GB")
    if specs.get("storage_gb"):
        label = {"ssd": "SSD", "hdd": "HDD"}.get(specs.get("storage_kind"), "")
        parts.append(f"{specs['storage_gb']}GB {label}".strip())
    if specs.get("gpu"):
        parts.append(specs["gpu"])
    return " · ".join(parts)
