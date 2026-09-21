#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

pdflatex -interaction=nonstopmode -halt-on-error tcc-grupo3-charlie.tex
bibtex tcc-grupo3-charlie
pdflatex -interaction=nonstopmode -halt-on-error tcc-grupo3-charlie.tex
pdflatex -interaction=nonstopmode -halt-on-error tcc-grupo3-charlie.tex

