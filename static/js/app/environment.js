import { LOCAL_HOSTNAMES } from './state.js';

export function isLocalEnvironment() {
    return LOCAL_HOSTNAMES.includes(window.location.hostname);
}
