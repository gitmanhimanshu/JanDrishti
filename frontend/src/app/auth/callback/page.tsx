'use client';

/**
 * OAuth return landing (spec 5).
 *
 * Exchanges the code for a session, then sends the user back to wherever they
 * were when we interrupted them — never to the home page, if we can avoid it.
 */
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { readStoredPendingAction } from '@/features/authentication/auth-context';
import { api } from '@/services/api-client';
import type { SessionPayload } from '@/types/api';

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackShell message="Completing sign-in…" />}>
      <CallbackHandler />
    </Suspense>
  );
}

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { completeSignIn } = useAuth();
  const [error, setError] = useState<string | null>(null);

  // React 18 mounts effects twice in development; exchanging a single-use code
  // twice would fail the second time and show a spurious error.
  const hasExchanged = useRef(false);

  useEffect(() => {
    if (hasExchanged.current) return;
    hasExchanged.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const oauthError = searchParams.get('error');

    if (oauthError) {
      setError('Sign-in was cancelled.');
      return;
    }
    if (!code) {
      setError('That sign-in link is incomplete.');
      return;
    }

    void (async () => {
      try {
        const session = await api.post<SessionPayload>(
          '/auth/google/callback/',
          { code, state },
          { anonymous: true },
        );
        completeSignIn(session);

        const stored = readStoredPendingAction();
        const destination =
          session.next || stored?.returnPath || (session.requires_onboarding ? '/welcome' : '/');
        router.replace(session.requires_onboarding ? '/welcome' : destination);
      } catch {
        setError('We could not complete that sign-in. Please try again.');
      }
    })();
  }, [completeSignIn, router, searchParams]);

  if (error) {
    return (
      <CallbackShell message={error}>
        <button
          type="button"
          onClick={() => router.push('/')}
          className="mt-6 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Back to JanDrishti
        </button>
      </CallbackShell>
    );
  }

  return <CallbackShell message="Completing sign-in…" />;
}

function CallbackShell({
  message,
  children,
}: {
  message: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-sm text-ink-600" role="status">
        {message}
      </p>
      {children}
    </div>
  );
}
