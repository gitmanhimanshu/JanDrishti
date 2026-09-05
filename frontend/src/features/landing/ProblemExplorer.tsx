import Link from 'next/link';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { ProblemCardView } from '@/features/problems/ProblemCard';
import type { ProblemCard } from '@/types/api';

/**
 * The problem explorer preview.
 *
 * When the platform has real problems, this shows them — the same card
 * component the live listing uses, so the preview cannot drift from reality.
 *
 * When it is empty, it shows a labelled *sample* instead of nothing. That
 * label is not decoration: inventing plausible-looking civic reports and
 * presenting them as real would undermine the one thing this platform sells,
 * which is that what you see actually happened.
 */

const SAMPLE = [
  {
    title: 'Pothole on Main Road',
    location: 'Sector 12, Pune',
    category: 'Infrastructure · Roads',
    support: 47,
    status: 'WORK_IN_PROGRESS',
    updated: '2 days ago',
  },
  {
    title: 'Garbage collection missed for 11 days',
    location: 'Ward 4, Nagpur',
    category: 'Waste Management',
    support: 128,
    status: 'ACKNOWLEDGED',
    updated: '5 hours ago',
  },
  {
    title: 'Broken streetlights near the school gate',
    location: 'Kalyani Nagar, Pune',
    category: 'Infrastructure · Streetlights',
    support: 63,
    status: 'UNDER_REVIEW',
    updated: '1 day ago',
  },
  {
    title: 'Water supply irregular for three weeks',
    location: 'Shivaji Nagar, Nashik',
    category: 'Water & Sanitation',
    support: 214,
    status: 'DEPARTMENT_ASSIGNED',
    updated: '6 hours ago',
  },
  {
    title: 'Public hospital out of essential medicines',
    location: 'Civil Lines, Nagpur',
    category: 'Healthcare',
    support: 302,
    status: 'INSPECTION',
    updated: '3 days ago',
  },
  {
    title: 'Open drain beside the primary school',
    location: 'Hadapsar, Pune',
    category: 'Water & Sanitation',
    support: 89,
    status: 'RESOLVED',
    updated: '1 week ago',
  },
] as const;

export function ProblemExplorer({ problems }: { problems: ProblemCard[] }) {
  const isLive = problems.length > 0;
  // A single real card stranded in a three-column grid looks broken. Below a
  // full row, show what is real *and* the sample beneath it, each labelled,
  // rather than padding the grid with invented rows.
  const showSampleToo = problems.length < 3;

  return (
    <section aria-labelledby="explorer-heading" className="border-b border-ink-200 bg-white">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-500">
              Problem explorer
            </p>
            <h2
              id="explorer-heading"
              className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
            >
              See what your community is facing
            </h2>
            <p className="mt-3 leading-relaxed text-ink-500">
              Filter by category, area, status or urgency. Every problem carries its location,
              its evidence and how many people it affects.
            </p>
          </div>
          <Link
            href="/problems"
            className="shrink-0 rounded-xl border border-ink-300 bg-white px-5 py-2.5 text-sm font-semibold text-brand-900 transition hover:border-brand-300 hover:bg-brand-50"
          >
            Open the explorer →
          </Link>
        </div>

        {isLive && (
          <>
            <SectionLabel tone="live">
              Raised on this deployment — {problems.length}{' '}
              {problems.length === 1 ? 'problem' : 'problems'}
            </SectionLabel>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {problems.map((problem) => (
                <ProblemCardView key={problem.id} problem={problem} />
              ))}
            </div>
          </>
        )}

        {showSampleToo && (
          <>
            <SectionLabel tone="sample">
              {isLive
                ? 'Sample view — how the explorer looks once a city is active'
                : 'Sample view — nothing has been raised on this deployment yet'}
            </SectionLabel>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {SAMPLE.map((item) => (
                <SampleCard key={item.title} item={item} />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function SectionLabel({
  tone,
  children,
}: {
  tone: 'live' | 'sample';
  children: React.ReactNode;
}) {
  const isLive = tone === 'live';
  return (
    <p
      className={`mt-9 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold ${
        isLive
          ? 'border-leaf-200 bg-leaf-50 text-leaf-800'
          : 'border-ink-200 bg-ink-50 text-ink-500'
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${isLive ? 'bg-leaf-500' : 'bg-ink-400'}`}
      />
      {children}
    </p>
  );
}

function SampleCard({ item }: { item: (typeof SAMPLE)[number] }) {
  return (
    <article className="flex flex-col rounded-xl border border-ink-200 bg-white p-5 opacity-90">
      <StatusBadge status={item.status} />

      <h3 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-brand-900">
        {item.title}
      </h3>

      <p className="mt-2 text-sm text-ink-500">{item.location}</p>
      <p className="mt-0.5 text-xs text-ink-400">{item.category}</p>

      <div className="mt-auto flex items-center justify-between pt-4 text-xs text-ink-500">
        <span className="font-medium text-ink-700">
          {item.support.toLocaleString('en-IN')} supporting
        </span>
        <span>{item.updated}</span>
      </div>
    </article>
  );
}
