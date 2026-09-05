'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { api } from '@/services/api-client';
import type { Notification } from '@/types/api';

/**
 * Unread badge plus a short dropdown.
 *
 * Polls rather than holding a socket open: the alert volume on a civic platform
 * is low, and a minute of latency on "your report was acknowledged" costs
 * nothing while a websocket per visitor costs a great deal at scale.
 */
const POLL_INTERVAL_MS = 60_000;

export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const loadCount = useCallback(async () => {
    try {
      const { unread: count } = await api.get<{ unread: number }>('/notifications/unread-count/');
      setUnread(count);
    } catch {
      /* a failed poll is not worth interrupting the page for */
    }
  }, []);

  useEffect(() => {
    void loadCount();
    const timer = window.setInterval(() => void loadCount(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [loadCount]);

  const openPanel = useCallback(async () => {
    setIsOpen((open) => !open);
    if (isOpen) return;
    try {
      const page = await api.page<Notification>('/notifications/?page_size=8');
      setItems(page.results);
    } catch {
      setItems([]);
    }
  }, [isOpen]);

  const markAllRead = useCallback(async () => {
    try {
      await api.post('/notifications/mark-read/', {});
      setUnread(0);
      setItems((current) => current.map((item) => ({ ...item, is_read: true })));
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => void openPanel()}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={isOpen}
        className="relative rounded-lg p-2 text-ink-500 transition hover:bg-ink-50 hover:text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        <BellIcon />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-1 w-80 rounded-xl border border-ink-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-ink-100 px-4 py-2.5">
            <span className="text-sm font-semibold text-ink-900">Notifications</span>
            {unread > 0 && (
              <button
                type="button"
                onClick={() => void markAllRead()}
                className="text-xs font-medium text-brand-700 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-ink-500">
                Nothing yet. Follow a problem to hear when it moves.
              </p>
            ) : (
              items.map((item) => (
                <Link
                  key={item.id}
                  href={item.link_path || '/'}
                  onClick={() => setIsOpen(false)}
                  className={`block border-b border-ink-50 px-4 py-3 transition hover:bg-ink-50 ${
                    item.is_read ? '' : 'bg-brand-50/40'
                  }`}
                >
                  <p className="text-sm font-medium text-ink-900">{item.title}</p>
                  {item.body && <p className="mt-0.5 text-xs text-ink-500">{item.body}</p>}
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M6 8a4 4 0 1 1 8 0c0 3 1 4.5 1.5 5h-11C5 12.5 6 11 6 8Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M8.5 15.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
