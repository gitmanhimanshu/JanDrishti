'use client';

/**
 * The login prompt (spec 60).
 *
 * Message is contextual — "Login to support this issue", not a generic wall —
 * because the user is mid-action and the prompt should read as a small step in
 * what they were already doing.
 *
 * Accessibility: focus moves into the dialog, Escape closes, focus is trapped
 * while open and returned to the trigger on close.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '@/services/api-client';
import type { SessionPayload } from '@/types/api';

import { useAuth } from './auth-context';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }): void;
          renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? '';

export function AuthRequiredModal() {
  const { pendingAction, closeLoginPrompt, completeSignIn } = useAuth();
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  const isOpen = pendingAction !== null;

  const exchangeCredential = useCallback(
    async (credential: string) => {
      setIsSigningIn(true);
      setError(null);
      try {
        const session = await api.post<SessionPayload>(
          '/auth/google/callback/',
          { id_token: credential },
          { anonymous: true },
        );
        completeSignIn(session);
      } catch {
        setError('That sign-in did not complete. Please try again.');
      } finally {
        setIsSigningIn(false);
      }
    },
    [completeSignIn],
  );

  // Focus management.
  useEffect(() => {
    if (!isOpen) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeLoginPrompt();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
      previouslyFocused.current?.focus();
    };
  }, [isOpen, closeLoginPrompt]);

  // Google Identity Services button.
  useEffect(() => {
    if (!isOpen || !GOOGLE_CLIENT_ID || !googleButtonRef.current) return;
    const google = window.google;
    if (!google) return;

    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => void exchangeCredential(response.credential),
    });
    google.accounts.id.renderButton(googleButtonRef.current, {
      theme: 'outline',
      size: 'large',
      width: 320,
      text: 'continue_with',
      shape: 'pill',
    });
  }, [isOpen, exchangeCredential]);

  const startRedirectFlow = useCallback(async () => {
    setIsSigningIn(true);
    setError(null);
    try {
      const { authorization_url } = await api.post<{ authorization_url: string }>(
        '/auth/google/start/',
        { next: pendingAction?.returnPath ?? window.location.pathname },
        { anonymous: true },
      );
      window.location.href = authorization_url;
    } catch {
      setError('Google sign-in is not available right now.');
      setIsSigningIn(false);
    }
  }, [pendingAction]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/50 p-4 backdrop-blur-sm sm:items-center"
      onClick={closeLoginPrompt}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        aria-describedby="auth-modal-description"
        tabIndex={-1}
        className="w-full max-w-md animate-fade-up rounded-2xl bg-white p-6 shadow-xl outline-none sm:p-8"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="auth-modal-title" className="text-xl font-semibold text-ink-900">
          {pendingAction.label}
        </h2>
        <p id="auth-modal-description" className="mt-2 text-sm leading-relaxed text-ink-600">
          You need a JanDrishti account to take part. Browsing stays open to everyone — signing
          in is only needed to contribute.
        </p>

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-6 space-y-3">
          <div ref={googleButtonRef} className="flex justify-center" />
          <button
            type="button"
            onClick={() => void startRedirectFlow()}
            disabled={isSigningIn}
            className="flex w-full items-center justify-center gap-3 rounded-xl border border-ink-200 bg-white px-4 py-3 text-sm font-medium text-ink-800 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
          >
            <GoogleMark />
            {isSigningIn ? 'Opening Google…' : 'Continue with Google'}
          </button>
          <button
            type="button"
            onClick={closeLoginPrompt}
            className="w-full rounded-xl px-4 py-2.5 text-sm text-ink-500 transition hover:text-ink-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            Cancel
          </button>
        </div>

        <p className="mt-5 text-center text-xs leading-relaxed text-ink-400">
          Signing in with Google confirms your account. It does not verify any professional
          claim — that is a separate, reviewed process.
        </p>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.93v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.93a9 9 0 0 0 0 8.1l3.04-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.46 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .93 4.95l3.04 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}
