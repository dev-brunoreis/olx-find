# olx-find

CLI que busca anúncios na OLX Brasil e ordena do melhor custo/benefício para o pior.

A busca em si fica no [omkarcloud/olx-brazil-scraper](https://github.com/omkarcloud/olx-brazil-scraper) (submodule em `vendor/olx-brazil-scraper`). Este projeto só chama a API local, extrai specs e ranqueia.

## Subir o scraper

Docker:

```bash
docker compose up olx-scraper
```

Sem Docker:

```bash
./scripts/start-scraper.sh
```

A API fica em `http://localhost:8000`. Confira com:

```bash
curl -s "http://localhost:8000/health"
```

Se a resposta vier com `blocked`, a Cloudflare da OLX recusou o IP. Defina um proxy residencial (saída no Brasil funciona melhor) e suba de novo:

```bash
OLX_BRAZIL_PROXY=http://user:pass@host:port docker compose up olx-scraper
```

## Instalar o CLI

Python 3.11+.

```bash
python -m pip install -e .
```

## Usar

```bash
olx-find --list-filters --category informatica/notebooks
olx-find "i5" --category informatica/notebooks --state sp --max-price 5200 \
  --filters "nt=3,nme=3" --pages 2 > out.csv
olx-find "notebook" --min-price 1500 --max-price 4000 --details > out.csv
```

`nt=3` é notebook gamer e `nme=3` é 32 GB de RAM. Cada chave aceita um valor por busca. Os códigos mudam por categoria: confirme com `--list-filters`.

Flags:

| Flag | Efeito |
| --- | --- |
| `--pages` | Páginas de `/ads/search` (50 anúncios cada, default 2) |
| `--state` | UF, enviada como `location` (ex.: `sp`) |
| `--location` | UF, caminho regional ou id de `/locations/search`. Não combine com `--state` |
| `--category` | Caminho ou código (ex.: `informatica/notebooks`) |
| `--sort` | `relevance` (default), `newest` ou `lowest_price` |
| `--seller-type` | `private` ou `professional` |
| `--condition` | `new`, `used_excellent`, `used_good`, `refurbished` ou `defective` |
| `--filters` | Filtros da categoria, `chave=valor` separados por vírgula |
| `--list-filters` | Lista os filtros de `--category` e não busca anúncios |
| `--min-price` / `--max-price` | Faixa de preço em BRL |
| `--details` | Busca `/ads/details/batch` para descrição e atributos |
| `--api-base` | URL do scraper (default `http://localhost:8000` ou `OLX_API_BASE`) |

A saída é um CSV no stdout (rank, score, preço, CPU, RAM, armazenamento, GPU, título, local e link), do melhor custo/benefício para o pior. Redirecione para um arquivo, como no exemplo acima. Mensagens de erro ficam no stderr.

## Como o ranking funciona

Extratores e scorers são plugáveis (`extract/` e `score/`).

- **Notebook** entra quando a busca ou o título fala em notebook/laptop. Lê CPU, RAM, SSD/HDD e GPU do texto e dos atributos. O score é `pontos de hardware / preço` (maior = melhor custo/benefício).
- **Genérico** é o fallback: quantos termos da busca aparecem no anúncio, ponderado pelo preço. Serve para qualquer outra coisa.

GPU dedicada e um scorer com LLM ficam de fora deste MVP: entram como módulos novos, sem mexer no client.
