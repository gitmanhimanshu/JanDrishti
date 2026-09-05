import { formatDateTime } from '@/lib/format';
import type { TimelineEvent } from '@/types/api';

/**
 * The proof-of-work timeline (spec 34).
 *
 * Append-only and public. When there is nothing but the original report, the
 * timeline says so — an issue nobody has acted on should look like one.
 */
const KIND_MARKERS: Record<string, { icon: string; className: string }> = {
  REPORTED: { icon: '📝', className: 'bg-ink-100 text-ink-700' },
  STATUS_CHANGED: { icon: '→', className: 'bg-blue-50 text-blue-700' },
  DEPARTMENT_ASSIGNED: { icon: '🏛', className: 'bg-blue-50 text-blue-700' },
  GOVERNMENT_RESPONSE: { icon: '💬', className: 'bg-blue-50 text-blue-700' },
  EVIDENCE_ADDED: { icon: '📎', className: 'bg-ink-100 text-ink-700' },
  EVIDENCE_VERIFIED: { icon: '✓', className: 'bg-green-50 text-green-700' },
  INSPECTION: { icon: '🔍', className: 'bg-amber-50 text-amber-800' },
  PROGRESS_UPDATE: { icon: '🔧', className: 'bg-indigo-50 text-indigo-700' },
  PROJECT_LINKED: { icon: '🏗', className: 'bg-indigo-50 text-indigo-700' },
  CLUSTERED: { icon: '🔗', className: 'bg-brand-50 text-brand-800' },
  RESOLVED: { icon: '✓', className: 'bg-green-50 text-green-700' },
};

export function ProblemTimeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="mt-4 rounded-xl border border-dashed border-ink-200 p-6 text-center text-sm text-ink-500">
        Nothing has happened on this issue yet.
      </p>
    );
  }

  return (
    <ol className="mt-4">
      {events.map((event, index) => {
        const marker = KIND_MARKERS[event.kind] ?? {
          icon: '•',
          className: 'bg-ink-100 text-ink-700',
        };
        const isLast = index === events.length - 1;

        return (
          <li key={event.id} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span
                aria-hidden="true"
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${marker.className}`}
              >
                {marker.icon}
              </span>
              {!isLast && <span aria-hidden="true" className="my-1 w-px flex-1 bg-ink-200" />}
            </div>

            <div className={isLast ? 'pb-1' : 'pb-6'}>
              <p className="text-sm font-semibold text-ink-900">{event.title}</p>
              {event.description && (
                <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-ink-600">
                  {event.description}
                </p>
              )}
              <p className="mt-1.5 text-xs text-ink-400">
                {formatDateTime(event.created_at)}
                {event.actor_label && ` · ${event.actor_label}`}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
