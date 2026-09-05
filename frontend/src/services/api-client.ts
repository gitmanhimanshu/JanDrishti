/**
 * The one HTTP client.
 *
 * Everything that talks to the backend goes through here, which is what makes
 * three things true in one place rather than fifty:
 *
 * - the API envelope is unwrapped consistently, so callers get data or an error
 *   and never a half-parsed response;
 * - an expired access token is refreshed once, transparently, with concurrent
 *   callers sharing the single refresh rather than stampeding;
 * - a 401 on a *read* is not treated as a failure, because reads are public and
 *   an anonymous visitor is a normal visitor on this platform.
 */
import type { ApiEnvelope, ApiError, PageMeta, Paginated } from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
const SERVER_API_URL = process.env.API_URL_INTERNAL ?? API_URL;

const ACCESS_TOKEN_KEY = 'jd.access_token';
const REFRESH_TOKEN_KEY = 'jd.refresh_token';

export class ApiRequestError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = error.code;
    this.details = error.details;
  }

  /** True when the only thing wrong is that the visitor is not signed in. */
  get isAuthError(): boolean {
    return this.status === 401 || this.code === 'AUTHENTICATION_REQUIRED';
  }
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------
// sessionStorage rather than localStorage: a token that survives until the tab
// closes is a smaller window than one that survives indefinitely, and this app
// has no "remember me on a shared machine" requirement.
export const tokenStore = {
  get access(): string | null {
    if (typeof window === 'undefined') return null;
    return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
  },
  get refresh(): string | null {
    if (typeof window === 'undefined') return null;
    return window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
  },
  set(access: string, refresh: string): void {
    if (typeof window === 'undefined') return;
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, access);
    window.sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear(): void {
    if (typeof window === 'undefined') return;
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

// ---------------------------------------------------------------------------
// Refresh coordination
// ---------------------------------------------------------------------------
// One in-flight refresh at a time. Without this, a page that fires six requests
// on mount would send six refreshes, and rotation would invalidate five of them
// and log the user out.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = tokenStore.refresh;
  if (!refreshToken) return false;

  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        tokenStore.clear();
        return false;
      }
      const body = (await response.json()) as ApiEnvelope<{
        access_token: string;
        refresh_token: string;
      }>;
      tokenStore.set(body.data.access_token, body.data.refresh_token);
      return true;
    } catch {
      tokenStore.clear();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

// ---------------------------------------------------------------------------
// Request
// ---------------------------------------------------------------------------
export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Skip the Authorization header even when a token exists. */
  anonymous?: boolean;
  /** Next.js fetch caching, for server components rendering public pages. */
  revalidate?: number;
  retryOnAuthFailure?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isServer = typeof window === 'undefined';
  const base = isServer ? SERVER_API_URL : API_URL;
  const { body, anonymous, revalidate, retryOnAuthFailure = true, ...init } = options;

  const headers = new Headers(init.headers);
  if (body !== undefined && !(body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (!anonymous && !isServer) {
    const token = tokenStore.access;
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${base}${path}`, {
    ...init,
    headers,
    body:
      body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    ...(revalidate !== undefined ? { next: { revalidate } } : {}),
  });

  // An expired access token is an ordinary condition, not an error: refresh
  // once and replay the original request.
  if (response.status === 401 && retryOnAuthFailure && !anonymous && !isServer) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return request<T>(path, { ...options, retryOnAuthFailure: false });
    }
  }

  let payload: ApiEnvelope<T> | null = null;
  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    payload = null;
  }

  if (!response.ok || payload?.success === false) {
    throw new ApiRequestError(
      response.status,
      payload?.error ?? {
        code: 'NETWORK_ERROR',
        message: 'We could not reach JanDrishti. Please check your connection.',
      },
    );
  }

  return (payload as ApiEnvelope<T>).data;
}

async function requestPage<T>(path: string, options: RequestOptions = {}): Promise<Paginated<T>> {
  const isServer = typeof window === 'undefined';
  const base = isServer ? SERVER_API_URL : API_URL;
  const headers = new Headers(options.headers);
  if (!options.anonymous && !isServer) {
    const token = tokenStore.access;
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${base}${path}`, {
    ...options,
    headers,
    body: undefined,
    ...(options.revalidate !== undefined ? { next: { revalidate: options.revalidate } } : {}),
  });

  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T[]> | null;
  if (!response.ok || !payload?.success) {
    throw new ApiRequestError(
      response.status,
      payload?.error ?? { code: 'NETWORK_ERROR', message: 'Could not load results.' },
    );
  }
  return { results: payload.data ?? [], meta: (payload.meta as PageMeta) ?? null };
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  page: <T>(path: string, options?: RequestOptions) =>
    requestPage<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE', body }),
};

/**
 * For server components rendering public pages.
 *
 * Returns a fallback instead of throwing: a statistics widget that cannot load
 * should leave the page standing with an empty state, not take it down.
 */
export async function fetchPublic<T>(path: string, fallback: T, revalidate = 60): Promise<T> {
  try {
    return await api.get<T>(path, { anonymous: true, revalidate });
  } catch {
    return fallback;
  }
}

export async function fetchPublicPage<T>(path: string, revalidate = 60): Promise<Paginated<T>> {
  try {
    return await api.page<T>(path, { anonymous: true, revalidate });
  } catch {
    return { results: [], meta: null };
  }
}
