export const API_BASE = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function api(path, { method = 'GET', body, signal } = {}) {
  const timeout = AbortSignal.timeout(15000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method, signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail.map(error => `${error.loc.slice(1).join(' ')}: ${error.msg}`).join('. ')
        : typeof detail === 'string' ? detail : `Request failed (${response.status}).`;
      throw new Error(message);
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError' && signal?.aborted) throw error;
    if (error.name === 'TimeoutError') throw new Error('The API took too long to respond. Check your connection and try again.');
    if (error instanceof TypeError) throw new Error('Cannot reach the API. Check that the backend is running and its URL and CORS origins are configured.');
    throw error;
  }
}
