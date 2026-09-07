#!/usr/bin/env bash
set -euo pipefail
OWNER="${1:-YucongDuan}"
REPO="${2:-DIKWP-COMMONBRIDGE-85}"
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required"; exit 1; }
python -m unittest discover -s tests -v
python tools/static_audit.py
if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  echo "Repository exists: $OWNER/$REPO"
else
  gh repo create "$OWNER/$REPO" --public --description "Any person. Any lawful AI tier. One verifiable contribution." --source . --remote origin
fi
git add .
git commit -m "Release COMMONBRIDGE-85 v1.0.0" || true
git branch -M main
git push -u origin main
git tag -f v1.0.0
git push -f origin v1.0.0
gh repo edit "$OWNER/$REPO" --enable-issues --enable-discussions --homepage "https://$OWNER.github.io/$REPO/"
gh release create v1.0.0 --title "COMMONBRIDGE-85 v1.0.0" --notes-file PUBLIC_LAUNCH_TEXT.md || true
printf '\nPin this repository manually on the GitHub profile.\n'
