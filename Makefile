PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
UVICORN ?= .venv/bin/uvicorn

.PHONY: install seed seed-augmented run test demo-setup

install:
	$(PIP) install -r requirements.txt

seed:
	PYTHONPATH=. $(PYTHON) scripts/import_sample_events.py

seed-augmented:
	DATA_FILE=data/sample_events_augmented.json PYTHONPATH=. $(PYTHON) scripts/import_sample_events.py

run:
	$(UVICORN) app.main:app --reload

test:
	$(PYTHON) -m pytest

demo-setup:
	$(MAKE) install
	$(MAKE) seed
