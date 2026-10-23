.PHONY: tools collect analyze test all

tools:
	./tools/install.sh

collect:
	./scripts/collect.sh

analyze:
	python3 -m kst

test:
	python3 -m pytest -q

all: collect analyze
