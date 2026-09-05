'use client';

/**
 * The community invite: a slim banner at the top and a floating card at the
 * bottom.
 *
 * Both are dismissible and both remember the dismissal, because an invite that
 * cannot be sent away is an advertisement. The bottom card waits a few seconds
 * before appearing so it never interrupts the first read of the page, and it
 * respects `prefers-reduced-motion` by simply being there rather than sliding.
 */
import { useCallback, useEffect, useState } from 'react';

import { COMMUNITY_COPY, DISMISS_DAYS, WHATSAPP_INVITE_URL } from '@/lib/community';

const BANNER_KEY = 'jd.community.banner_dismissed_at';
const POPUP_KEY = 'jd.community.popup_dismissed_at';
const POPUP_DELAY_MS = 4000;

function wasDismissedRecently(key: string): boolean {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return false;
    const ageDays = (Date.now() - Number(raw)) / 86_400_000;
    return ageDays < DISMISS_DAYS;
  } catch {
    // Private mode or blocked storage: show it, rather than crashing.
    return false;
  }
}

function remember(key: string): void {
  try {
    window.localStorage.setItem(key, String(Date.now()));
  } catch {
    /* nothing to do */
  }
}

/* --------------------------------------------------------------- banner */

export function CommunityBanner() {
  // Start hidden so the server and first client render agree; storage is only
  // readable after mount, and a mismatch would be a hydration error.
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!wasDismissedRecently(BANNER_KEY)) setIsVisible(true);
  }, []);

  const dismiss = useCallback(() => {
    remember(BANNER_KEY);
    setIsVisible(false);
  }, []);

  if (!isVisible) return null;

  return (
    <div className="relative z-50 bg-leaf-800 text-white">
      <div className="mx-auto flex max-w-content items-center gap-3 px-4 py-2.5 sm:px-6">
        <WhatsAppMark className="hidden h-5 w-5 shrink-0 sm:block" />
        <p className="min-w-0 flex-1 text-sm leading-snug">
          <span className="font-semibold">{COMMUNITY_COPY.short}</span>
          <span className="hidden text-leaf-100 sm:inline"> — {COMMUNITY_COPY.banner}</span>
        </p>
        <a
          href={WHATSAPP_INVITE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 rounded-lg bg-white px-3.5 py-1.5 text-xs font-bold text-leaf-800 transition hover:bg-leaf-50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-leaf-800"
        >
          Join
        </a>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss community invite"
          className="shrink-0 rounded-md p-1 text-leaf-200 transition hover:bg-leaf-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-white"
        >
          <CloseMark className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- popup */

export function CommunityPopup() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (wasDismissedRecently(POPUP_KEY)) return;
    const timer = window.setTimeout(() => setIsVisible(true), POPUP_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  const dismiss = useCallback(() => {
    remember(POPUP_KEY);
    setIsVisible(false);
  }, []);

  if (!isVisible) return null;

  return (
    <div
      role="complementary"
      aria-label="Community invite"
      className="fixed bottom-4 right-4 z-50 w-[min(22rem,calc(100vw-2rem))] animate-fade-up"
    >
      <div className="overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-2xl shadow-brand-950/25">
        <div className="flex items-start gap-3 p-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-leaf-50 text-leaf-700">
            <WhatsAppMark className="h-6 w-6" />
          </span>

          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold text-brand-900">{COMMUNITY_COPY.popupTitle}</p>
            <p className="mt-1 text-xs leading-relaxed text-ink-500">
              {COMMUNITY_COPY.popupBody}
            </p>
          </div>

          <button
            type="button"
            onClick={dismiss}
            aria-label="Dismiss community invite"
            className="-mr-1 -mt-1 shrink-0 rounded-md p-1 text-ink-400 transition hover:bg-ink-100 hover:text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <CloseMark className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center gap-2 border-t border-ink-100 bg-ink-50 px-4 py-3">
          <a
            href={WHATSAPP_INVITE_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={dismiss}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-leaf-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-leaf-800 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
          >
            <WhatsAppMark className="h-4 w-4" />
            {COMMUNITY_COPY.cta}
          </a>
          <button
            type="button"
            onClick={dismiss}
            className="rounded-lg px-3 py-2.5 text-sm font-medium text-ink-500 transition hover:text-ink-800"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- marks */

export function WhatsAppMark({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12.04 2C6.6 2 2.2 6.4 2.2 11.84c0 1.74.46 3.44 1.32 4.94L2.1 22l5.35-1.4a9.8 9.8 0 0 0 4.59 1.17h.01c5.43 0 9.84-4.4 9.84-9.84 0-2.63-1.02-5.1-2.88-6.96A9.78 9.78 0 0 0 12.04 2Zm0 17.98h-.01a8.2 8.2 0 0 1-4.17-1.14l-.3-.18-3.1.81.83-3.02-.2-.31a8.15 8.15 0 0 1-1.25-4.3c0-4.51 3.68-8.18 8.2-8.18a8.13 8.13 0 0 1 5.79 2.4 8.1 8.1 0 0 1 2.4 5.79c0 4.52-3.68 8.19-8.19 8.19Zm4.49-6.13c-.24-.12-1.45-.72-1.68-.8-.22-.08-.39-.12-.55.12-.16.25-.63.8-.77.97-.14.16-.28.18-.53.06-.24-.12-1.04-.38-1.98-1.22-.73-.65-1.23-1.46-1.37-1.7-.14-.25-.02-.38.11-.5.11-.11.24-.28.36-.42.12-.15.16-.25.24-.41.08-.17.04-.31-.02-.43-.06-.12-.55-1.33-.76-1.82-.2-.48-.4-.41-.55-.42h-.47c-.16 0-.43.06-.65.31-.22.24-.85.83-.85 2.03s.87 2.35.99 2.51c.12.17 1.72 2.63 4.17 3.69.58.25 1.04.4 1.39.51.59.19 1.12.16 1.54.1.47-.07 1.45-.59 1.65-1.17.2-.57.2-1.06.14-1.16-.06-.1-.22-.16-.46-.28Z" />
    </svg>
  );
}

function CloseMark({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" className={className} aria-hidden="true">
      <path
        d="m4 4 8 8M12 4l-8 8"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
