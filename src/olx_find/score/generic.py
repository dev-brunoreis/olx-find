"""Fallback: mais termos da busca e preço menor sobem no ranking."""

from olx_find.models import Ad


class GenericScorer:
    def supports(self, specs: dict) -> bool:
        return True

    def score(self, ad: Ad, specs: dict) -> float:
        matched = len(specs.get("matched") or [])
        total = len(specs.get("query_tokens") or []) or 1
        relevance = matched / total
        if not ad.price or ad.price <= 0:
            return round(relevance, 4)
        return round(relevance * 1000 / ad.price, 4)
