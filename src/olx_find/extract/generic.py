"""Fallback: quais termos da busca aparecem no anúncio."""

import re
import unicodedata

from olx_find.models import Ad

_TOKEN = re.compile(r"[a-z0-9]+", re.I)
_STOP = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "um", "uma", "o", "a"}


class GenericSpecExtractor:
    def __init__(self, query: str):
        self.query = query
        self.tokens = _tokens(query)

    def supports(self, query: str, ad: Ad) -> bool:
        return True

    def extract(self, ad: Ad) -> dict:
        haystack = set(_tokens(ad.text()))
        matched = [token for token in self.tokens if token in haystack]
        return {
            "kind": "generic",
            "matched": matched,
            "query_tokens": self.tokens,
            "summary": " ".join(matched),
        }


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    seen: list[str] = []
    for token in _TOKEN.findall(normalized.lower()):
        if token in _STOP or token in seen:
            continue
        seen.append(token)
    return seen
