#!/usr/bin/env bash
# sensitive-data-guard — one-command installer.
#
#   ./install.sh                 # install sdg + the ro_RO language model
#   SDG_LOCALES="ro_RO md_MD" ./install.sh   # extra packs (md_MD shares the RO model)
#   SDG_NO_MODEL=1 ./install.sh  # skip the spaCy model download (CI / offline)
#
# Creates a local .venv, installs the package, downloads the spaCy NER model(s),
# then runs `sdg certify` so the machine gets a passport. Never touches system
# Python. Idempotent.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

PY="${SDG_PYTHON:-python3.11}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi
echo "==> Using interpreter: $($PY --version 2>&1) ($PY)"

if [ ! -d .venv ]; then
  echo "==> Creating virtualenv (.venv)"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
VPY=".venv/bin/python"

echo "==> Installing sdg (+ dev extras)"
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet -e ".[dev]"

# Map each requested locale to the spaCy model it needs.
# md_MD (Moldova) shares the Romanian model — Romanian is an official language.
locales="${SDG_LOCALES:-ro_RO}"
declare -A MODEL_FOR=( [ro_RO]="ro_core_news_lg" [md_MD]="ro_core_news_lg" )

if [ "${SDG_NO_MODEL:-0}" != "1" ]; then
  downloaded=""
  for loc in $locales; do
    model="${MODEL_FOR[$loc]:-}"
    if [ -z "$model" ]; then
      echo "!! No spaCy model mapping for locale '$loc' — skipping"
      continue
    fi
    case " $downloaded " in
      *" $model "*) continue ;;  # already pulled (e.g. ro_RO + md_MD)
    esac
    echo "==> Downloading spaCy model: $model (~600 MB, one-time)"
    "$VPY" -m spacy download "$model"
    downloaded="$downloaded $model"
  done
else
  echo "==> SDG_NO_MODEL=1 — skipping spaCy model download"
fi

echo "==> Verifying install"
"$VPY" -m pip show sensitive-data-guard >/dev/null
".venv/bin/sdg" version
".venv/bin/sdg" packs

echo "==> Certifying this machine (passport)"
if ".venv/bin/sdg" certify; then
  echo "==> Certified."
else
  echo "!! Certification reported issues (see above). Run '.venv/bin/sdg preflight'"
  echo "   to see which processing paths are enabled."
fi

cat <<'EOF'

Done. Activate the venv or call the binary directly:

  .venv/bin/sdg preflight          # which paths are enabled
  .venv/bin/sdg protocol list      # available work protocols

To let an agent use this skill, point its skill loader at SKILL.md in this repo.
EOF
