import Link from 'next/link';

import { PriorityBadge, StatusBadge } from '@/components/ui/StatusBadge';
import { formatRelative } from '@/lib/format';
import type { ProblemCard } from '@/types/api';

/**
 * The problem card (spec 12).
 *
 * A server component with no interactivity of its own: the whole card is a
 * link, and supporting happens on the detail page where the consequences are
 * visible. That keeps list pages renderable without JavaScript.
 */
export function ProblemCardView({ problem }: { problem: ProblemCard }) {
  return (
    <article className="group flex flex-col overflow-hidden rounded-xl border border-ink-200 bg-white transition hover:border-brand-300 hover:shadow-sm">
      <Link href={`/problems/${problem.id}`} className="flex flex-1 flex-col focus:outline-none">
        {problem.cover_image && (
          <div className="relative aspect-[16/9] overflow-hidden bg-ink-100">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={problem.cover_image.url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
            />
            {!problem.cover_image.verified && (
              <span className="absolute bottom-2 left-2 rounded bg-ink-900/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
                Unverified
              </span>
            )}
          </div>
        )}

        <div className="flex flex-1 flex-col p-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={problem.status} label={problem.status_display} />
            <PriorityBadge priority={problem.priority} label={problem.priority_display} />
          </div>

          <h3 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-ink-900 group-hover:text-brand-800">
            {problem.title}
          </h3>

          <p className="mt-2 flex items-center gap-1.5 text-sm text-ink-500">
            <PinIcon />
            <span className="truncate">{problem.location.display || 'Location not specified'}</span>
          </p>

          {problem.category && (
            <p className="mt-1 text-xs text-ink-400">{problem.category.name}</p>
          )}

          <div className="mt-auto flex items-center gap-4 pt-4 text-xs text-ink-500">
            <span className="font-medium text-ink-700">
              {problem.support_count.toLocaleString('en-IN')} supporting
            </span>
            {problem.report_count > 1 && (
              <span title="Independent reports of the same issue">
                {problem.report_count} reports
              </span>
            )}
            {problem.evidence_count > 0 && <span>{problem.evidence_count} files</span>}
            <span className="ml-auto shrink-0">{formatRelative(problem.last_activity_at)}</span>
          </div>
        </div>
      </Link>

      {problem.cluster_id && (
        <Link
          href={`/clusters/${problem.cluster_id}`}
          className="border-t border-ink-100 bg-ink-50/60 px-5 py-2 text-xs text-ink-600 transition hover:bg-ink-100"
        >
          Part of a grouped issue — see all reports →
        </Link>
      )}
    </article>
  );
}

function PinIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="shrink-0">
      <path
        d="M7 1.5c2.2 0 4 1.8 4 4 0 3-4 7-4 7s-4-4-4-7c0-2.2 1.8-4 4-4Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <circle cx="7" cy="5.5" r="1.4" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}
