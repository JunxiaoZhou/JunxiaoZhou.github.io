.PHONY: build scholar publications

build:
	python3 scripts/build.py

scholar:
	python3 scripts/fetch_scholar_metrics.py

publications:
	python3 scripts/fetch_publication_metadata.py
