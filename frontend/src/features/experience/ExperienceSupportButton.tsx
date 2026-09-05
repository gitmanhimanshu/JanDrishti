'use client';

import { useCallback, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { formatCount } from '@/lib/format';
import { api } from '@/services/api-client';

interface SupportResponse {
  support_count: number;
  already_supported: boolean;
  viewer_has_supported: boolean;
}

/** "I support this idea" — agreement, deliberately not a claim of correctness. */
export function ExperienceSupportButton({
  experienceId,
  initialCount,
  initiallySupported,
}: {
  experienceId: string;
  initialCount: number;
  initiallySupported: boolean;
}) {
  const { requireAuth } = useAuth();
  const [count, setCount] = useState(initialCount);
  const [supported, setSupported] = useState(initiallySupported);
  const [isBusy, setIsBusy] = useState(false);

  const submit = useCallback(async () => {
    setIsBusy(true);
    try {
      const result = supported
        ? await api.delete<SupportResponse>(`/experiences/${experienceId}/support/`)
        : await api.post<SupportResponse>(`/experiences/${experienceId}/support/`, {});
      setCount(result.support_count);
      setSupported(result.viewer_has_supported);
    } catch {
      /* the displayed count stays as the server last reported it */
    } finally {
      setIsBusy(false);
    }
  }, [experienceId, supported]);

  return (
    <div>
      <button
        type="button"
        disabled={isBusy}
        aria-pressed={supported}
        onClick={() =>
          requireAuth(submit, {
            label: 'Login to support this idea',
            returnPath: `/experience/${experienceId}`,
          })
        }
        className={`w-full rounded-xl px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-70 ${
          supported
            ? 'bg-brand-100 text-brand-900 hover:bg-brand-200'
            : 'bg-brand-600 text-white hover:bg-brand-700'
        }`}
      >
        {supported ? 'You support this' : 'I support this'}
        <span className="ml-1.5 tabular-nums opacity-80">· {formatCount(count)}</span>
      </button>
      <p className="mt-2 text-center text-xs text-ink-400">
        Support signals agreement, not proof.
      </p>
    </div>
  );
}
