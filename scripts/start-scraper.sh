#!/usr/bin/env bash
# Sobe a API local do omkarcloud/olx-brazil-scraper sem Docker.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/vendor/olx-brazil-scraper"
if [[ -f requirements.txt ]]; then
  python -m pip install -q -r requirements.txt
fi
exec python run.py
