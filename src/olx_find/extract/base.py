from typing import Protocol

from olx_find.models import Ad


class SpecExtractor(Protocol):
    def supports(self, query: str, ad: Ad) -> bool: ...

    def extract(self, ad: Ad) -> dict: ...
