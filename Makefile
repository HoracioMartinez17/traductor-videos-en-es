PYTHON=.venv/bin/python
UVICORN=.venv/bin/uvicorn

.PHONY: dev run

dev:
	$(UVICORN) app:app --host 0.0.0.0 --port 5000 --reload

run:
	$(PYTHON) app.py