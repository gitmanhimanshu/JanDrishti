/**
 * Loading, empty and error states (spec 59).
 *
 * Every list on this platform can legitimately be empty — a new deployment has
 * no problems in it, and a filter can exclude everything. The empty state says
 * so plainly rather than showing invented placeholder content.
 */
import Link from 'next/link';
import type { ReactNode } from 'react';

export function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-ink-200 bg-white p-5" aria-hidden="true">
      <div className="h-4 w-3/4 rounded bg-ink-100" />
      <div className="mt-3 h-3 w-1/2 rounded bg-ink-100" />
      <div className="mt-6 flex gap-3">
        <div className="h-6 w-20 rounded-full bg-ink-100" />
        <div className="h-6 w-24 rounded-full bg-ink-100" />
      </div>
    </div>
  );
}

export function ListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-busy="true">
      <span className="sr-only">Loading…</span>
      {Array.from({ length: count }, (_, index) => (
        <CardSkeleton key={index} />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-ink-200 bg-white/60 px-6 py-14 text-center">
      <h3 className="text-base font-semibold text-ink-800">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-500">{description}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'We could not load this just now. Please try again.',
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-red-200 bg-red-50/60 px-6 py-10 text-center"
    >
      <h3 className="text-base font-semibold text-red-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-red-800">{description}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-900 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function PrimaryLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
    >
      {children}
    </Link>
  );
}

export function SecondaryLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center rounded-xl border border-ink-300 bg-white px-5 py-2.5 text-sm font-semibold text-ink-800 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
    >
      {children}
    </Link>
  );
}
