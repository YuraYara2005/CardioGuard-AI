import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ── Request interceptor: attach bearer token if present ──────────────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('cg_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor: surface error messages cleanly ─────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error?.response?.data?.detail ??
      error?.message ??
      'Unknown API error';
    console.error('[CardioGuard API]', message);
    return Promise.reject(new Error(message));
  },
);

export default apiClient;
