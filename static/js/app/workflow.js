import { elements } from './dom.js';
import { FALLBACK_TRIGGER_MS, MAX_VIDEO_DURATION_SECONDS, POLLING_TIMEOUT_MS, state } from './state.js';
import { isLocalEnvironment } from './environment.js';
import { discardJob, downloadJobResult, pollJobStatus, triggerFallback } from './api.js';
import {
    clearVideoPreview,
    getProcessingMode,
    normalizeErrorMessage,
    setResult,
    startProgress,
    stopProgress,
    updateModeUI
} from './ui.js';

export function stopPolling() {
    if (state.currentPolling) {
        clearInterval(state.currentPolling);
        state.currentPolling = null;
    }
}

async function handleJobCompletion(jobId) {
    try {
        setResult('Descargando video traducido...', 'info');
        const blob = await downloadJobResult(jobId);

        clearVideoPreview();
        state.translatedVideoUrl = window.URL.createObjectURL(blob);
        elements.translatedVideo.src = state.translatedVideoUrl;
        elements.downloadLink.href = state.translatedVideoUrl;
        elements.videoPanel.classList.add('active');
        state.currentJobId = null;
        setResult('¡Video traducido correctamente! Si cierras esta página sin descargarlo, se perderá.', 'success');
    } catch (_error) {
        setResult('Error al obtener el video traducido.', 'error');
    }
}

export async function clearSavedVideo() {
    if (state.currentJobId) {
        await discardJob(state.currentJobId);
        state.currentJobId = null;
    }

    clearVideoPreview();
    setResult('Vista limpiada. Puedes traducir un nuevo video.', 'info');
}

function setSubmitState(isBusy) {
    elements.submitBtn.disabled = isBusy;
    elements.cancelBtn.hidden = !isBusy;
    elements.cancelBtn.disabled = false;
    elements.submitBtn.textContent = isBusy ? 'Enviando...' : 'Subir y traducir';
}

function getVideoFileDuration(file) {
    return new Promise((resolve, reject) => {
        const objectUrl = URL.createObjectURL(file);
        const video = document.createElement('video');
        video.preload = 'metadata';

        const cleanup = () => {
            URL.revokeObjectURL(objectUrl);
            video.removeAttribute('src');
            video.load();
        };

        video.onloadedmetadata = () => {
            const duration = video.duration;
            cleanup();
            if (!Number.isFinite(duration) || duration <= 0) {
                reject(new Error('No se pudo leer la duración del video'));
                return;
            }
            resolve(duration);
        };

        video.onerror = () => {
            cleanup();
            reject(new Error('No se pudo leer la duración del video'));
        };

        video.src = objectUrl;
    });
}

export async function handleSubmit(event) {
    event.preventDefault();

    if (state.currentAbortController || state.currentPolling) {
        return;
    }

    const hasFile = Boolean(elements.fileInput.files[0]);
    const providedUrl = elements.videoUrlInput.value.trim();

    if (!hasFile && !providedUrl) {
        setResult('Selecciona un archivo o pega una URL de YouTube para continuar.', 'error');
        return;
    }

    const formData = new FormData();
    if (hasFile) {
        const selectedFile = elements.fileInput.files[0];
        try {
            const duration = await getVideoFileDuration(selectedFile);
            if (duration > MAX_VIDEO_DURATION_SECONDS) {
                const durationSeconds = Math.floor(duration);
                const minutes = Math.floor(durationSeconds / 60);
                const seconds = durationSeconds % 60;
                const maxMinutes = Math.floor(MAX_VIDEO_DURATION_SECONDS / 60);
                setResult(
                    `Error: Hermano, te pasaste 😅 ¿Qué piensas, que tengo un ordenador de la NASA o qué? El límite es de ${maxMinutes} minutos por video y este dura ${minutes}:${String(seconds).padStart(2, '0')}.`,
                    'error'
                );
                return;
            }
        } catch (_error) {
            setResult('Error: No se pudo leer la duración del video antes de subirlo.', 'error');
            return;
        }
        formData.append('file', selectedFile);
    }

    setSubmitState(true);
    setResult('Subiendo video al servidor...', 'info');
    state.currentAbortController = new AbortController();
    state.fallbackRequested = false;
    state.pendingSinceMs = 0;
    startProgress('Subiendo video');

    try {
        const processingTarget = getProcessingMode();
        const isUrlFlow = !hasFile && Boolean(providedUrl);
        const urlTarget = isUrlFlow && processingTarget === 'pc' ? 'pc' : processingTarget;

        if (processingTarget === 'pc' && hasFile) {
            setResult('Procesando en local...', 'info');
            startProgress('Procesando en local');

            const localResponse = await fetch('/upload', {
                method: 'POST',
                body: formData,
                signal: state.currentAbortController.signal
            });

            if (!localResponse.ok) {
                const error = await localResponse.json();
                const message = normalizeErrorMessage(error.detail || error.error || 'Error al procesar el video.');
                setResult(`Error: ${message}`, 'error');
                return;
            }

            const blob = await localResponse.blob();
            clearVideoPreview();
            state.translatedVideoUrl = window.URL.createObjectURL(blob);
            elements.translatedVideo.src = state.translatedVideoUrl;
            elements.downloadLink.href = state.translatedVideoUrl;
            elements.videoPanel.classList.add('active');
            state.currentJobId = null;
            setResult('¡Video traducido correctamente! Si cierras esta página sin descargarlo, se perderá.', 'success');
            return;
        }

        const uploadResponse = isUrlFlow
            ? await fetch(`/upload-from-url-async?target=${urlTarget}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: providedUrl }),
                signal: state.currentAbortController.signal
            })
            : await fetch(`/upload-async?target=${processingTarget}`, {
                method: 'POST',
                body: formData,
                signal: state.currentAbortController.signal
            });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            const message = normalizeErrorMessage(error.detail || error.error || 'Error al subir el video.');
            setResult(`Error: ${message}`, 'error');
            return;
        }

        const { job_id } = await uploadResponse.json();
        state.currentJobId = job_id;
        state.currentAbortController = null;

        setResult('Video encolado. Iniciando procesamiento...', 'info');
        startProgress('En cola / procesando');
        state.pendingSinceMs = Date.now();

        state.currentPolling = setInterval(async () => {
            const jobStatus = await pollJobStatus(job_id);
            if (!jobStatus) {
                return;
            }

            const elapsedSinceQueuedMs = state.pendingSinceMs ? Date.now() - state.pendingSinceMs : 0;
            if (elapsedSinceQueuedMs >= POLLING_TIMEOUT_MS) {
                stopPolling();
                stopProgress();
                state.fallbackRequested = false;
                state.pendingSinceMs = 0;
                setResult('Error: el procesamiento tardó demasiado (más de 3 minutos). Revisa el worker y vuelve a intentar.', 'error');
                setSubmitState(false);
                return;
            }

            if (jobStatus.status === 'completed') {
                stopPolling();
                stopProgress();
                state.fallbackRequested = false;
                state.pendingSinceMs = 0;
                await handleJobCompletion(job_id);
                setSubmitState(false);
                return;
            }

            if (jobStatus.status === 'failed') {
                stopPolling();
                stopProgress();
                state.fallbackRequested = false;
                state.pendingSinceMs = 0;
                if (state.currentJobId) {
                    await discardJob(state.currentJobId);
                    state.currentJobId = null;
                }
                setResult(`Error al procesar: ${jobStatus.error_message || 'Error desconocido'}`, 'error');
                setSubmitState(false);
                return;
            }

            if (jobStatus.status === 'processing') {
                startProgress('Procesando en remoto');
                if (jobStatus.worker_id === 'render-fallback') {
                    setResult('Procesando en remoto. Este paso puede tardar unos minutos.', 'info');
                }
                return;
            }

            if (jobStatus.status !== 'pending') {
                return;
            }

            if (!state.pendingSinceMs) {
                state.pendingSinceMs = Date.now();
            }

            const pendingMs = Date.now() - state.pendingSinceMs;
            if (!state.fallbackRequested && processingTarget === 'cloud' && pendingMs >= FALLBACK_TRIGGER_MS) {
                state.fallbackRequested = true;
                setResult('Inicializando procesamiento remoto...', 'info');
                startProgress('Inicializando procesamiento remoto');
                try {
                    await triggerFallback(job_id);
                } catch (_error) {
                    setResult('No se pudo activar el fallback ahora. Seguimos esperando worker disponible.', 'info');
                    state.fallbackRequested = false;
                }
                return;
            }

            if (!state.fallbackRequested) {
                if (processingTarget === 'pc') {
                    if (pendingMs >= 15000) {
                        setResult('Video en cola local. Verifica que el worker esté conectado a http://127.0.0.1:5000.', 'info');
                    } else {
                        setResult('Video en cola para procesamiento local.', 'info');
                    }
                } else {
                    setResult('Video en cola para procesamiento remoto.', 'info');
                }
            }
        }, 2000);
    } catch (error) {
        if (error.name === 'AbortError') {
            setResult('Subida cancelada. Puedes iniciar una nueva traducción.', 'info');
        } else {
            setResult('No se pudo conectar con el servidor. Intenta de nuevo.', 'error');
        }
    } finally {
        if (state.currentAbortController) {
            state.currentAbortController = null;
        }

        if (!state.currentPolling) {
            stopProgress();
            setSubmitState(false);
        }
    }
}

export function handleCancel() {
    if (state.currentAbortController) {
        elements.cancelBtn.disabled = true;
        state.currentAbortController.abort();
        return;
    }

    if (state.currentPolling) {
        stopPolling();
        stopProgress();
        setSubmitState(false);
        setResult('Polling cancelado. El video seguirá procesándose en segundo plano.', 'info');
    }
}

export function handleDownload() {
    state.wasDownloaded = true;
    if (state.currentJobId) {
        discardJob(state.currentJobId);
        state.currentJobId = null;
    }
}

export function handleBeforeUnload() {
    if (state.currentJobId) {
        const blob = new Blob([], { type: 'application/octet-stream' });
        navigator.sendBeacon(`/jobs/${state.currentJobId}/discard`, blob);
        state.currentJobId = null;
    }
}

export function initMode() {
    if (isLocalEnvironment()) {
        state.selectedMode = 'pc';
        elements.modeToggle.hidden = true;
    } else {
        state.selectedMode = 'cloud';
    }

    updateModeUI();
}
