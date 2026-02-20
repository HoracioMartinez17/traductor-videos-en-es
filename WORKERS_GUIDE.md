# Arquitectura de Workers – Procesamiento Distribuido

Sistema de procesamiento asíncrono mediante workers distribuidos para traducción de videos.

## Arquitectura

```
Cliente → API (Render) → Cola Jobs (SQLite) → Worker Local → Resultado
```

### Flujo de procesamiento:

1. Cliente sube video → `POST /upload-async`
2. API encola job → Estado `pending` en DB
3. Worker obtiene job → `GET /jobs/next` (polling)
4. Worker reclama job → `POST /jobs/{id}/claim` → Estado `processing`
5. Worker descarga input → `GET /jobs/{id}/download-input`
6. Worker procesa video → Transcripción, traducción, TTS
7. Worker sube resultado → `POST /jobs/{id}/upload-result`
8. Cliente obtiene resultado → Polling + descarga

---

## Seguridad

### 1. Autenticación

Endpoints de workers protegidos con header `X-API-Key`.

Generar token:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Configuración:
- Render: Variable `WORKER_API_KEY` en settings
- Worker: Parámetro `--api-key` al ejecutar

### 2. Endpoints protegidos

Requieren API key válida:
- `GET /jobs/next`
- `POST /jobs/{id}/claim`
- `POST /jobs/{id}/upload-result`
- `GET /jobs/{id}/download-input`

### 3. Endpoints públicos

- `GET /jobs/{id}` – Consultar estado
- `GET /jobs/{id}/download` – Descargar resultado (solo completados)

---

## Configuración

### Variables de entorno

Render → Settings → Environment:

```env
WORKER_API_KEY=<token-generado>
WHISPER_MODEL=tiny.en
```

### Instalación worker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Ejecución

```bash
python worker.py \
  --api-url https://app.onrender.com \
  --api-key <token>
```

Parámetros:
- `--api-url`: URL base de la API
- `--api-key`: Token de autenticación
- `--poll-interval`: Intervalo de consulta en segundos (default: 5)
- `--worker-id`: Identificador del worker (default: hostname-pid)

---

## Ventajas

- Procesamiento local con mayor capacidad de cómputo
- Sin límites de timeout del servicio de hosting
- Costos reducidos en infraestructura cloud
- Escalabilidad horizontal mediante múltiples workers

---

## Troubleshooting

### Worker no encuentra jobs

Verificar:
- API key correcto en ambos extremos
- URL sin barra final
- Jobs pendientes en base de datos

### Error 403

Token incorrecto. Verificar que `WORKER_API_KEY` coincida.

### Job bloqueado en "processing"

Worker puede haber terminado inesperadamente. Revisar logs y actualizar estado manualmente si es necesario.

---

## Optimizaciones

### GPU

Modificar `transcription_service.py`:
```python
WhisperModel(model, device="cuda", compute_type="float16")
```

### Múltiples workers

Ejecutar con diferentes `worker-id`:
```bash
python worker.py --api-url ... --api-key ... --worker-id worker-1 &
python worker.py --api-url ... --api-key ... --worker-id worker-2 &
```

---

## Mejoras sugeridas

- Rate limiting en endpoints públicos
- Sistema de ownership por usuario
- Limpieza automática de jobs antiguos
- Logging y auditoría
- Validación de integridad de uploads
