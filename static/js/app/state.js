export const state = {
    translatedVideoUrl: null,
    timerInterval: null,
    startTimeMs: 0,
    currentAbortController: null,
    currentPolling: null,
    currentJobId: null,
    wasDownloaded: false,
    selectedMode: 'cloud',
    pendingSinceMs: 0,
    fallbackRequested: false
};

export const FALLBACK_TRIGGER_MS = 20000;
export const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', '::1'];
export const MAX_VIDEO_DURATION_SECONDS = 300;
export const POLLING_TIMEOUT_MS = 180000;
