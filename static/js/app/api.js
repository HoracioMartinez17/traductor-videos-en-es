export async function pollJobStatus(jobId) {
    try {
        const response = await fetch(`/jobs/${jobId}`);
        if (!response.ok) {
            throw new Error('Error al consultar estado del job');
        }

        return await response.json();
    } catch (error) {
        console.error('Error en polling:', error);
        return null;
    }
}

export async function downloadJobResult(jobId) {
    const response = await fetch(`/jobs/${jobId}/download`);
    if (!response.ok) {
        throw new Error('Error al descargar resultado');
    }

    return await response.blob();
}

export async function discardJob(jobId) {
    if (!jobId) {
        return;
    }

    try {
        await fetch(`/jobs/${jobId}/discard`, { method: 'POST' });
    } catch (_error) {
        // noop
    }
}

export async function triggerFallback(jobId) {
    await fetch(`/jobs/${jobId}/process-fallback`, { method: 'POST' });
}
