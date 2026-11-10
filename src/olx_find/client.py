"""Cliente HTTP da API local do omkarcloud/olx-brazil-scraper."""

from __future__ import annotations

import httpx

from olx_find.models import Ad

BATCH_SIZE = 10


class OlxApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class OlxApiClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 90.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(
        self,
        query: str,
        *,
        pages: int = 1,
        location: str | None = None,
        category: str | None = None,
        sort: str | None = None,
        seller_type: str | None = None,
        condition: str | None = None,
        filters: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
    ) -> list[Ad]:
        ads: list[Ad] = []
        seen: set[int] = set()
        for page in range(1, pages + 1):
            payload = self._get(
                "/ads/search",
                {
                    "query": query,
                    "page": page,
                    "location": location,
                    "category": category,
                    "sort": sort,
                    "seller_type": seller_type,
                    "condition": condition,
                    "filters": filters,
                    "price_min": price_min,
                    "price_max": price_max,
                },
            )
            for item in payload.get("results") or []:
                ad = ad_from_payload(item)
                if ad.id is not None and ad.id in seen:
                    continue
                if ad.id is not None:
                    seen.add(ad.id)
                ads.append(ad)
            total_pages = int(payload.get("total_pages") or 0)
            if total_pages and page >= total_pages:
                break
            if not payload.get("results"):
                break
        return ads

    def category_filters(self, category: str) -> dict:
        return self._get("/categories/filters", {"category": category})

    def enrich(self, ads: list[Ad]) -> list[Ad]:
        """Preenche descrição e atributos via /ads/details/batch (até 10 por call)."""
        by_id = {ad.id: ad for ad in ads if ad.id is not None}
        ids = list(by_id)
        for start in range(0, len(ids), BATCH_SIZE):
            chunk = ids[start : start + BATCH_SIZE]
            payload = self._get("/ads/details/batch", {"ads": ",".join(str(i) for i in chunk)})
            for item in payload.get("results") or []:
                detailed = ad_from_payload(item)
                current = by_id.get(detailed.id)
                if current is None:
                    continue
                current.description = detailed.description or current.description
                if detailed.attributes:
                    current.attributes = {**current.attributes, **detailed.attributes}
                if detailed.price is not None:
                    current.price = detailed.price
                    current.price_text = detailed.price_text
                if detailed.url:
                    current.url = detailed.url
                if detailed.location:
                    current.location = detailed.location
        return ads

    def _get(self, path: str, params: dict) -> dict:
        clean = {key: value for key, value in params.items() if value not in (None, "")}
        try:
            response = httpx.get(f"{self.base_url}{path}", params=clean, timeout=self.timeout)
        except httpx.ConnectError as exc:
            raise OlxApiError(
                f"não conectou em {self.base_url}. Suba o scraper com "
                "`docker compose up olx-scraper` ou `scripts/start-scraper.sh`."
            ) from exc
        except httpx.HTTPError as exc:
            raise OlxApiError(f"falha HTTP em {path}: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise OlxApiError(f"resposta não-JSON de {path} ({response.status_code})", response.status_code) from exc
        if response.status_code >= 400:
            message = body.get("error") if isinstance(body, dict) else None
            raise OlxApiError(message or f"{path} retornou {response.status_code}", response.status_code)
        if not isinstance(body, dict):
            raise OlxApiError(f"resposta inesperada de {path}")
        return body


def ad_from_payload(item: dict) -> Ad:
    price = item.get("price") if isinstance(item.get("price"), dict) else {}
    location = item.get("location")
    return Ad(
        id=_as_int(item.get("id")),
        title=(item.get("title") or "").strip(),
        url=(item.get("link") or item.get("url") or "").strip(),
        price=_as_float(price.get("amount")),
        price_text=price.get("text"),
        location=_location_text(location),
        description=(item.get("description") or "").strip(),
        attributes=_attributes(item.get("attributes")),
    )


def _attributes(raw) -> dict[str, str]:
    out: dict[str, str] = {}
    if not isinstance(raw, list):
        return out
    for prop in raw:
        if not isinstance(prop, dict):
            continue
        label = (prop.get("label") or prop.get("name") or "").strip()
        value = prop.get("value")
        if value in (None, "") and isinstance(prop.get("values"), list):
            value = ", ".join(str(v) for v in prop["values"] if v)
        if label and value not in (None, ""):
            out[label] = str(value).strip()
    return out


def _location_text(location) -> str:
    if isinstance(location, str):
        return location.strip()
    if not isinstance(location, dict):
        return ""
    parts = [
        location.get("neighbourhood") or location.get("name"),
        location.get("municipality"),
        location.get("state"),
    ]
    return " · ".join(str(part).strip() for part in parts if part)


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
