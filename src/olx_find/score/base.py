from typing import Protocol

from olx_find.models import Ad


class Scorer(Protocol):
    def supports(self, specs: dict) -> bool: ...

    def score(self, ad: Ad, specs: dict) -> float: ...
