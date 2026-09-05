'use client';

/**
 * Authentication state and the `requireAuth` mechanism (spec 5).
 *
 * The central idea: an anonymous visitor never gets blocked *before* they act.
 * They browse freely, press "Support this issue", and only then meet a login
 * prompt — and once they sign in, the action they were attempting is carried
 * out for them. They are never dropped on the home page having forgotten what
 * they were doing.
 *
 * That is implemented by holding the pending action in a ref across the OAuth
 * round trip, and replaying it on success.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { ApiRequestError, api, tokenStore } from '@/services/api-client';
import type { CurrentUser, SessionPayload } from '@/types/api';

const PENDING_ACTION_KEY = 'jd.pending_action';

export interface PendingAction {
  /** Human-readable, shown in the login prompt: "Login to support this issue". */
  label: string;
  /** Where the user should end up after signing in. */
  returnPath: string;
}

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** The action awaiting a login, if any. */
  pendingAction: PendingAction | null;
  /**
   * Run `action` if signed in; otherwise open the login prompt and run it
   * once the user comes back.
   */
  requireAuth: (action: () => void | Promise<void>, context: PendingAction) => void;
  completeSignIn: (session: SessionPayload) => void;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  closeLoginPrompt: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  // Held in a ref, not state: the callback itself must survive re-renders
  // without triggering them, and it is not serialisable.
  const pendingCallback = useRef<(() => void | Promise<void>) | null>(null);

  const loadUser = useCallback(async () => {
    if (!tokenStore.access && !tokenStore.refresh) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      setUser(await api.get<CurrentUser>('/users/me/'));
    } catch (error) {
      // Not being signed in is the normal state here, not a failure worth
      // surfacing to a visitor who is simply browsing.
      if (!(error instanceof ApiRequestError && error.isAuthError)) {
        console.error('Could not load the current account', error);
      }
      tokenStore.clear();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const requireAuth = useCallback(
    (action: () => void | Promise<void>, context: PendingAction) => {
      if (user) {
        void action();
        return;
      }
      pendingCallback.current = action;
      setPendingAction(context);
      // Also persisted, because a full-page OAuth redirect discards the ref.
      // On return the app can at least restore the user to the right page.
      try {
        window.sessionStorage.setItem(PENDING_ACTION_KEY, JSON.stringify(context));
      } catch {
        /* storage may be unavailable; the in-memory path still works */
      }
    },
    [user],
  );

  const completeSignIn = useCallback((session: SessionPayload) => {
    tokenStore.set(session.access_token, session.refresh_token);
    setUser(session.user);
    setPendingAction(null);

    const action = pendingCallback.current;
    pendingCallback.current = null;
    try {
      window.sessionStorage.removeItem(PENDING_ACTION_KEY);
    } catch {
      /* ignore */
    }
    // Replay what they were trying to do before we interrupted them.
    if (action) void action();
  }, []);

  const signOut = useCallback(async () => {
    const refresh = tokenStore.refresh;
    try {
      if (refresh) await api.post('/auth/signout/', { refresh_token: refresh });
    } catch {
      /* signing out locally matters more than the server acknowledging it */
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  const closeLoginPrompt = useCallback(() => {
    pendingCallback.current = null;
    setPendingAction(null);
    try {
      window.sessionStorage.removeItem(PENDING_ACTION_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      pendingAction,
      requireAuth,
      completeSignIn,
      signOut,
      refreshUser: loadUser,
      closeLoginPrompt,
    }),
    [user, isLoading, pendingAction, requireAuth, completeSignIn, signOut, loadUser, closeLoginPrompt],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return context;
}

export function readStoredPendingAction(): PendingAction | null {
  try {
    const raw = window.sessionStorage.getItem(PENDING_ACTION_KEY);
    return raw ? (JSON.parse(raw) as PendingAction) : null;
  } catch {
    return null;
  }
}
