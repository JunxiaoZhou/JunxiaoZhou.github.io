.PHONY: build scholar

build:
	python3 scripts/build.py

scholar:
	python3 scripts/fetch_scholar_metrics.py
