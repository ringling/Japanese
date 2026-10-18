PY := .venv/bin/python
IDS = $(shell $(PY) -c "import json;print(' '.join(s['id'] for s in json.load(open('stories/index.json'))))")

# make story ID=<video id> LESSON=<n> [ANKI=1]   build + smoke test + nav rebuild
story:
	$(PY) build_story.py $(ID) --lesson $(LESSON) $(if $(ANKI),--add-to-anki,)
	node smoke.js
	python3 ../build_nav.py

# make check   rebuild every story strictly (fails on unchecked glosses) and smoke-test the reader
check:
	$(PY) build_story.py $(IDS) --lesson $(or $(LESSON),7) --strict
	node smoke.js

.PHONY: story check
