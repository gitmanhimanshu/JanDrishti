'use client';

/**
 * "I face this problem" (spec 14).
 *
 * The clearest expression of the public-first model: an anonymous visitor may
 * press this. Only then do they meet the login prompt, and afterwards the
 * support is recorded for them without their having to find the page again.
 *
 * The wording is deliberate. This is not a Like — it is a citizen stating that
 * a public problem affects them too, and there is no way to press it twice or
 * to press it negatively.
 */
import { useCallback, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { ApiRequestError, api } from '@/services/api-client';
import { formatCount } from '@/lib/format';

interface SupportResponse {
  support_count: number;
  already_supported: boolean;
  viewer_has_supported: boolean;
}

export function SupportButton({
  problemId,
  initialCount,
  initiallySupported,
  title,
}: {
  problemId: string;
  initialCount: number;
  initiallySupported: boolean;
  title: string;
}) {
  const { requireAuth } = useAuth();
  const [count, setCount] = useState(initialCount);
  const [supported, setSupported] = useState(initiallySupported);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setIsBusy(true);
    setError(null);

    // Optimistic, because the server is the authority on the count and will
    // correct us a moment later either way.
    const previousCount = count;
    const previousSupported = supported;
    setSupported(!previousSupported);
    setCount(previousSupported ? Math.max(previousCount - 1, 0) : previousCount + 1);

    try {
      const result = previousSupported
        ? await api.delete<SupportResponse>(`/problems/${problemId}/support/`)
        : await api.post<SupportResponse>(`/problems/${problemId}/support/`, {});
      setCount(result.support_count);
      setSupported(result.viewer_has_supported);
    } catch (caught) {
      setSupported(previousSupported);
      setCount(previousCount);
      setError(
        caught instanceof ApiRequestError
          ? caught.message
          : 'That did not go through. Please try again.',
      );
    } finally {
      setIsBusy(false);
    }
  }, [count, problemId, supported]);

  const onClick = () =>
    requireAuth(submit, {
      label: supported ? 'Login to update your support' : 'Login to support this issue',
      returnPath: `/problems/${problemId}`,
    });

  return (
    <div>
      <button
        type="button"
        onClick={onClick}
        disabled={isBusy}
        aria-pressed={supported}
        aria-label={
          supported
            ? `You have said you face this problem: ${title}`
            : `I face this problem too: ${title}`
        }
        className={`flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-70 ${
          supported
            ? 'bg-brand-100 text-brand-900 hover:bg-brand-200'
            : 'bg-brand-600 text-white hover:bg-brand-700'
        }`}
      >
        <HandIcon filled={supported} />
        {supported ? 'You face this problem' : 'I face this problem'}
        <span className="tabular-nums opacity-80">· {formatCount(count)}</span>
      </button>

      {error && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {error}
        </p>
      )}

      <p className="mt-2 text-center text-xs text-ink-400">
        {supported
          ? 'Your report is counted with everyone else affected.'
          : 'Adds your voice to everyone affected by this issue.'}
      </p>
    </div>
  );
}

function HandIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M5 8V4.2a1.2 1.2 0 1 1 2.4 0V7m0-1.3a1.2 1.2 0 1 1 2.4 0V7.5m0-1a1.2 1.2 0 1 1 2.4 0V10a4 4 0 0 1-4 4H7.2a3 3 0 0 1-2.3-1.1L2.6 10a1.2 1.2 0 0 1 1.8-1.6L5 9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill={filled ? 'currentColor' : 'none'}
        fillOpacity={filled ? 0.18 : 0}
      />
    </svg>
  );
}
