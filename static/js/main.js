import {
    clearSavedVideo,
    elements,
    handleBeforeUnload,
    handleCancel,
    handleDownload,
    handleSubmit,
    initMode,
    updateModeUI,
    state
} from './app/index.js';

const DEMO_URL = 'https://youtube.com/shorts/gix6uExbKKc?si=XikFAvp6tls4ibtM';

function bindEvents() {
    elements.fileInput.addEventListener('change', () => {
        elements.fileName.textContent = elements.fileInput.files[0]
            ? `Seleccionado: ${elements.fileInput.files[0].name}`
            : 'No has seleccionado ningún archivo.';
    });

    elements.form.addEventListener('submit', handleSubmit);
    elements.cancelBtn.addEventListener('click', handleCancel);
    elements.clearVideoBtn.addEventListener('click', clearSavedVideo);

    elements.modeLocalBtn.addEventListener('click', () => {
        state.selectedMode = 'pc';
        updateModeUI();
    });

    elements.modeCloudBtn.addEventListener('click', () => {
        state.selectedMode = 'cloud';
        updateModeUI();
    });

    elements.useDemoUrlBtn?.addEventListener('click', () => {
        elements.videoUrlInput.value = DEMO_URL;
        elements.videoUrlInput.focus();
        setTimeout(() => {
            elements.videoUrlInput.setSelectionRange(elements.videoUrlInput.value.length, elements.videoUrlInput.value.length);
        }, 0);
    });

    elements.copyDemoUrlBtn?.addEventListener('click', async () => {
        const originalText = elements.copyDemoUrlBtn.textContent;
        try {
            await navigator.clipboard.writeText(DEMO_URL);
            elements.copyDemoUrlBtn.textContent = 'Copiado';
        } catch (_error) {
            elements.copyDemoUrlBtn.textContent = 'No se pudo copiar';
        }

        setTimeout(() => {
            elements.copyDemoUrlBtn.textContent = originalText;
        }, 1200);
    });

    elements.downloadLink.addEventListener('click', handleDownload);
    window.addEventListener('beforeunload', handleBeforeUnload);
}

function init() {
    initMode();
    bindEvents();
}

init();
