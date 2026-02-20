PYTHON=.venv/bin/python
UVICORN=.venv/bin/uvicorn
API_URL?=https://traductor-videos-en-es.onrender.com
WORKER_PID_FILE=.worker.pid

ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: dev run worker worker-render worker-start worker-stop worker-status

dev:
	$(UVICORN) app:app --host 0.0.0.0 --port 5000 --reload

run:
	$(PYTHON) app.py

worker:
	@if [ -z "$(WORKER_API_KEY)" ]; then \
		echo "Falta WORKER_API_KEY. Ejecuta: make worker WORKER_API_KEY=tu_token"; \
		exit 1; \
	fi
	$(PYTHON) worker.py --api-url $(API_URL) --api-key $(WORKER_API_KEY)

worker-render:
	@$(MAKE) worker API_URL=https://traductor-videos-en-es.onrender.com WORKER_API_KEY="$(WORKER_API_KEY)"

worker-start:
	@if [ -z "$(WORKER_API_KEY)" ]; then \
		echo "Falta WORKER_API_KEY. Defínelo en .env o ejecuta: make worker-start WORKER_API_KEY=tu_token"; \
		exit 1; \
	fi
	@if [ -f "$(WORKER_PID_FILE)" ] && kill -0 "$$(cat $(WORKER_PID_FILE))" 2>/dev/null; then \
		echo "Worker ya está corriendo con PID $$(cat $(WORKER_PID_FILE))"; \
		exit 0; \
	fi
	@nohup $(PYTHON) worker.py --api-url $(API_URL) --api-key $(WORKER_API_KEY) > worker.log 2>&1 & echo $$! > $(WORKER_PID_FILE)
	@echo "Worker iniciado en segundo plano (PID $$(cat $(WORKER_PID_FILE))). Logs: worker.log"

worker-stop:
	@if [ ! -f "$(WORKER_PID_FILE)" ]; then \
		echo "No hay PID guardado. El worker no parece estar corriendo."; \
		exit 0; \
	fi
	@if kill -0 "$$(cat $(WORKER_PID_FILE))" 2>/dev/null; then \
		kill "$$(cat $(WORKER_PID_FILE))"; \
		echo "Worker detenido (PID $$(cat $(WORKER_PID_FILE)))"; \
	else \
		echo "El proceso del PID guardado ya no está activo."; \
	fi
	@rm -f $(WORKER_PID_FILE)

worker-status:
	@if [ -f "$(WORKER_PID_FILE)" ] && kill -0 "$$(cat $(WORKER_PID_FILE))" 2>/dev/null; then \
		echo "Worker activo (PID $$(cat $(WORKER_PID_FILE)))"; \
	else \
		echo "Worker detenido"; \
	fi