import { elements } from './dom.js';
import { state } from './state.js';
import { isLocalEnvironment } from './environment.js';

export function getProcessingMode() {
    return state.selectedMode;
}

export function setResult(message, type) {
    elements.result.className = type;
    elements.result.textContent = message;
}

export function normalizeErrorMessage(message) {
    const rawMessage = String(message || '');
    const lowerMessage = rawMessage.toLowerCase();

    if (lowerMessage.includes("sign in to confirm you're not a bot") || lowerMessage.includes('cookies')) {
        return 'YouTube bloqueó la descarga automática de este video. Prueba con otro enlace público o sube un archivo local.';
    }

    if (lowerMessage.includes('video unavailable') || lowerMessage.includes('private video')) {
        return 'No se pudo acceder al video de YouTube. Verifica la URL o usa un enlace público.';
    }

    if (rawMessage.includes('El video excede la duración máxima de 5 minutos')) {
        const durationMatch = rawMessage.match(/Duración:\s*(\d+)s/i);
        let durationText = '.';
        if (durationMatch) {
            const totalSeconds = Number(durationMatch[1]);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            durationText = ` y este dura ${minutes}:${String(seconds).padStart(2, '0')}.`;
        }
        return `Hermano, te pasaste 😅 ¿Qué piensas, que tengo un ordenador de la NASA o qué? El límite es de 5 minutos por video${durationText}`;
    }

    return rawMessage;
}

function formatElapsed(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const seconds = (totalSeconds % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
}

export function startProgress(message = 'Procesando traducción') {
    state.startTimeMs = Date.now();
    elements.elapsedTime.textContent = '00:00';
    elements.progressWrap.hidden = false;
    elements.progressWrap.querySelector('.progress-meta span:first-child').textContent = message;

    if (state.timerInterval) {
        clearInterval(state.timerInterval);
    }

    state.timerInterval = setInterval(() => {
        elements.elapsedTime.textContent = formatElapsed(Date.now() - state.startTimeMs);
    }, 250);
}

export function stopProgress() {
    elements.progressWrap.hidden = true;
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

export function clearVideoPreview() {
    if (state.translatedVideoUrl) {
        URL.revokeObjectURL(state.translatedVideoUrl);
        state.translatedVideoUrl = null;
    }

    elements.translatedVideo.removeAttribute('src');
    elements.translatedVideo.load();
    elements.downloadLink.href = '#';
    elements.videoPanel.classList.remove('active');
    state.wasDownloaded = false;
}

export function updateModeUI() {
    const isCloud = state.selectedMode === 'cloud';

    elements.modeCloudBtn.classList.toggle('active', isCloud);
    elements.modeLocalBtn.classList.toggle('active', !isCloud);

    if (isCloud) {
        elements.modeHelp.textContent = 'Procesamiento en la nube.';
        elements.modeWarning.textContent = 'En modo Nube, el procesamiento puede tardar más según la carga del servidor.';
        elements.modeWarning.hidden = false;
    } else {
        elements.modeHelp.textContent = 'Procesamiento en un equipo externo.';
        elements.modeWarning.textContent = 'Si eliges Remoto (PC), debe haber un worker de PC encendido para procesar el video.';
        elements.modeWarning.hidden = isLocalEnvironment();
    }
}
