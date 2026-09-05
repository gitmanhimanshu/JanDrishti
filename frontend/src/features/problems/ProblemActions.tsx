'use client';

/** Follow and share. Following needs an account; sharing never does. */
import { useCallback, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { api } from '@/services/api-client';

export function FollowButton({
  targetType,
  targetId,
}: {
  targetType: 'PROBLEM' | 'EXPERIENCE' | 'PROJECT' | 'USER';
  targetId: string;
}) {
  const { requireAuth } = useAuth();
  const [following, setFollowing] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  const toggle = useCallback(async () => {
    setIsBusy(true);
    const body = { target_type: targetType, target_id: targetId };
    try {
      if (following) {
        await api.delete('/social/follows/toggle/', body);
        setFollowing(false);
      } else {
        await api.post('/social/follows/toggle/', body);
        setFollowing(true);
      }
    } catch {
      /* leave the previous state; the next attempt can correct it */
    } finally {
      setIsBusy(false);
    }
  }, [following, targetId, targetType]);

  return (
    <button
      type="button"
      disabled={isBusy}
      onClick={() =>
        requireAuth(toggle, {
          label: 'Login to follow updates',
          returnPath: typeof window === 'undefined' ? '/' : window.location.pathname,
        })
      }
      aria-pressed={following}
      className="flex-1 rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
    >
      {following ? 'Following' : 'Follow'}
    </button>
  );
}

export function ShareButton({ title }: { title: string }) {
  const [copied, setCopied] = useState(false);

  const share = useCallback(async () => {
    const url = window.location.href;
    // The native sheet where it exists; a copied link everywhere else. Both
    // work for an anonymous visitor, because public URLs are the point.
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch {
        /* the user dismissed the sheet; fall through to copying */
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable; nothing useful to say */
    }
  }, [title]);

  return (
    <button
      type="button"
      onClick={() => void share()}
      className="flex-1 rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
    >
      {copied ? 'Link copied' : 'Share'}
    </button>
  );
}
