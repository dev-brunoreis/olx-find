"""CLI: busca anúncios e imprime o ranking de custo/benefício em CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys

from olx_find.client import OlxApiClient, OlxApiError
from olx_find.rank import RankedAd, rank_ads

_COLUMNS = (
    "rank",
    "score",
    "price",
    "cpu",
    "ram_gb",
    "storage_gb",
    "storage_kind",
    "gpu",
    "title",
    "location",
    "url",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="olx-find",
        description="Busca anúncios na OLX (via API local) e ranqueia por custo/benefício.",
    )
    parser.add_argument("query", help="o que você quer comprar, ex.: 'notebook i5 16gb'")
    parser.add_argument("--pages", type=int, default=2, help="páginas de /ads/search (default 2)")
    parser.add_argument("--state", help="UF, ex.: sp")
    parser.add_argument("--min-price", type=float, dest="min_price")
    parser.add_argument("--max-price", type=float, dest="max_price")
    parser.add_argument(
        "--details",
        action="store_true",
        help="busca a página de cada anúncio para specs mais ricas (mais lento)",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("OLX_API_BASE", "http://localhost:8000"),
        help="URL do scraper (default http://localhost:8000 ou OLX_API_BASE)",
    )
    args = parser.parse_args(argv)
    if args.pages < 1:
        parser.error("--pages deve ser >= 1")

    client = OlxApiClient(args.api_base)
    try:
        ads = client.search(
            args.query,
            pages=args.pages,
            location=args.state,
            price_min=args.min_price,
            price_max=args.max_price,
        )
        if args.details and ads:
            ads = client.enrich(ads)
    except OlxApiError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        if exc.status and exc.status >= 500 and "blocked" in str(exc).lower():
            print(
                "a OLX bloqueou o IP. Defina OLX_BRAZIL_PROXY (proxy residencial) e reinicie o scraper.",
                file=sys.stderr,
            )
        return 1

    if not ads:
        print("nenhum anúncio encontrado.", file=sys.stderr)
        write_csv([])
        return 0

    write_csv(rank_ads(args.query, ads))
    return 0


def write_csv(ranked: list[RankedAd], dest=None) -> None:
    """CSV no stdout. Preço com ponto decimal para ordenar na planilha."""
    out = dest if dest is not None else sys.stdout
    if dest is None and hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8")
    if dest is None and not out.isatty():
        out.write("\ufeff")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(_COLUMNS)
    for index, item in enumerate(ranked, start=1):
        specs = item.specs
        price = "" if item.ad.price is None else f"{item.ad.price:.2f}"
        writer.writerow(
            [
                index,
                item.score,
                price,
                specs.get("cpu") or "",
                specs.get("ram_gb") or "",
                specs.get("storage_gb") or "",
                specs.get("storage_kind") or "",
                specs.get("gpu") or "",
                item.ad.title.replace("\n", " ").strip(),
                item.ad.location,
                item.ad.url,
            ]
        )


if __name__ == "__main__":
    raise SystemExit(main())
