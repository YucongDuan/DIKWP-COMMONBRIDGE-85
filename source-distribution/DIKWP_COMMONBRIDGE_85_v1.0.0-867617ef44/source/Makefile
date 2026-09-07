.PHONY: test static-audit acceptance qa manifest

test:
	python -m unittest discover -s tests -v

static-audit:
	python tools/static_audit.py

acceptance:
	python tools/acceptance.py

qa: test static-audit acceptance

manifest:
	python tools/build_manifest.py
