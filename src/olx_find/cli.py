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
    parser.add_argument("query", nargs="?", help="o que você quer comprar, ex.: 'notebook i5 16gb'")
    parser.add_argument("--pages", type=int, default=2, help="páginas de /ads/search (default 2)")
    parser.add_argument("--state", help="UF, enviada como location (ex.: sp)")
    parser.add_argument(
        "--location",
        help="UF, caminho (estado-sp/sao-paulo-e-regiao) ou id de /locations/search",
    )
    parser.add_argument(
        "--category",
        help="caminho ou código da categoria (ex.: informatica/notebooks)",
    )
    parser.add_argument(
        "--sort",
        choices=("relevance", "newest", "lowest_price"),
        help="ordenação da OLX (default relevance)",
    )
    parser.add_argument(
        "--seller-type",
        choices=("private", "professional"),
        help="particular ou loja",
    )
    parser.add_argument(
        "--condition",
        choices=("new", "used_excellent", "used_good", "refurbished", "defective"),
        help="condição genérica da OLX; notebook usa o filtro nc (veja --list-filters)",
    )
    parser.add_argument(
        "--filters",
        help="filtros da categoria, chave=valor separados por vírgula (ex.: nt=3,nme=3)",
    )
    parser.add_argument(
        "--list-filters",
        action="store_true",
        help="lista os filtros de --category e sai, sem buscar anúncios",
    )
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
    if args.state and args.location:
        parser.error("use só um entre --state e --location")
    if args.list_filters and not args.category:
        parser.error("--list-filters precisa de --category")
    if not args.list_filters and not args.query:
        parser.error("informe o que buscar")

    client = OlxApiClient(args.api_base)
    if args.list_filters:
        try:
            payload = client.category_filters(args.category)
        except OlxApiError as exc:
            return _fail(exc)
        _print_filters(payload)
        return 0

    try:
        ads = client.search(
            args.query,
            pages=args.pages,
            location=args.location or args.state,
            category=args.category,
            sort=args.sort,
            seller_type=args.seller_type,
            condition=args.condition,
            filters=args.filters,
            price_min=args.min_price,
            price_max=args.max_price,
        )
        if args.details and ads:
            ads = client.enrich(ads)
    except OlxApiError as exc:
        return _fail(exc)

    if not ads:
        print("nenhum anúncio encontrado.", file=sys.stderr)
        write_csv([])
        return 0

    write_csv(rank_ads(args.query, ads))
    return 0


def _fail(exc: OlxApiError) -> int:
    print(f"erro: {exc}", file=sys.stderr)
    if exc.status and exc.status >= 500 and "blocked" in str(exc).lower():
        print(
            "a OLX bloqueou o IP. Defina OLX_BRAZIL_PROXY (proxy residencial) e reinicie o scraper.",
            file=sys.stderr,
        )
    return 1


def _print_filters(payload: dict) -> None:
    category = payload.get("category") or {}
    name = category.get("name") or category.get("path") or "categoria"
    print(f"{name}  ({payload.get('total_count', '?')} anúncios)")
    for item in payload.get("filters") or []:
        keys = [key for key in (item.get("query_keys") or []) if key]
        if not keys:
            continue
        print(f"\n{item.get('label') or item.get('name')}  [{','.join(keys)}]")
        values = item.get("values") or []
        if not values:
            print("  (sem lista de valores; a OLX trata como liga/desliga)")
            continue
        for value in values:
            if not isinstance(value, dict):
                continue
            print(f"  {value.get('value')}  {value.get('label')}")


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
