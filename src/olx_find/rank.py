from dataclasses import dataclass

from olx_find.extract.generic import GenericSpecExtractor
from olx_find.extract.notebook import NotebookSpecExtractor
from olx_find.models import Ad
from olx_find.score.generic import GenericScorer
from olx_find.score.notebook import NotebookValueScorer


@dataclass
class RankedAd:
    ad: Ad
    score: float
    specs: dict

    @property
    def summary(self) -> str:
        return self.specs.get("summary") or ""


def rank_ads(query: str, ads: list[Ad]) -> list[RankedAd]:
    specific = [(NotebookSpecExtractor(), NotebookValueScorer())]
    generic_extractor = GenericSpecExtractor(query)
    generic_scorer = GenericScorer()
    ranked: list[RankedAd] = []
    for ad in ads:
        specs = None
        scorer = None
        for extractor, candidate in specific:
            if not extractor.supports(query, ad):
                continue
            extracted = extractor.extract(ad)
            if candidate.supports(extracted):
                specs = extracted
                scorer = candidate
                break
        if scorer is None:
            specs = generic_extractor.extract(ad)
            scorer = generic_scorer
        ranked.append(RankedAd(ad=ad, score=scorer.score(ad, specs), specs=specs))
    ranked.sort(key=lambda item: (item.score, -(item.ad.price or 0)), reverse=True)
    return ranked
