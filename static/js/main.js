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

    elements.downloadLink.addEventListener('click', handleDownload);
    window.addEventListener('beforeunload', handleBeforeUnload);
}

function init() {
    initMode();
    bindEvents();
}

init();
