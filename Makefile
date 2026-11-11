.PHONY: install test run-backend run-frontend reproduce-experiments clean

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest

# Windows fallback for venv binaries
ifeq ($(OS),Windows_NT)
	PYTHON = .venv/Scripts/python.exe
	PIP = .venv/Scripts/pip.exe
	PYTEST = .venv/Scripts/pytest.exe
endif

install:
	python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	cd frontend && npm install

test:
	$(PYTEST) backend/tests -v

run-backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

reproduce-experiments:
	$(PYTHON) experiments/generate_synthetic.py
	$(PYTHON) experiments/run_all.py

clean:
	rm -rf storage/ .pytest_cache/ backend/**/__pycache__ frontend/dist

