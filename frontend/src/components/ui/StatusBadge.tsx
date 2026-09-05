/**
 * Status and evidence badges.
 *
 * Two rules encoded here rather than left to each caller:
 *
 * 1. Status colour carries meaning consistently across every surface, so a
 *    citizen learns the vocabulary once.
 * 2. Uploaded evidence and verified evidence never look the same (spec 17).
 *    The distinction is the whole credibility model, so it is not left to a
 *    subtle shade — the words differ too.
 */
import type { ProblemStatus, VerificationState } from '@/types/api';

const STATUS_STYLES: Record<string, { className: string; label: string }> = {
  SUBMITTED: { className: 'bg-ink-100 text-ink-700', label: 'Submitted' },
  UNDER_REVIEW: { className: 'bg-amber-50 text-amber-800', label: 'Under review' },
  VERIFIED: { className: 'bg-amber-50 text-amber-800', label: 'Verified' },
  DEPARTMENT_ASSIGNED: { className: 'bg-blue-50 text-blue-800', label: 'Department assigned' },
  ACKNOWLEDGED: { className: 'bg-blue-50 text-blue-800', label: 'Acknowledged' },
  INSPECTION: { className: 'bg-blue-50 text-blue-800', label: 'Inspection' },
  ACTION_PLANNED: { className: 'bg-indigo-50 text-indigo-800', label: 'Action planned' },
  WORK_STARTED: { className: 'bg-indigo-50 text-indigo-800', label: 'Work started' },
  WORK_IN_PROGRESS: { className: 'bg-indigo-50 text-indigo-800', label: 'Work in progress' },
  COMPLETED: { className: 'bg-brand-50 text-brand-800', label: 'Completed' },
  VERIFICATION: { className: 'bg-brand-50 text-brand-800', label: 'Being verified' },
  RESOLVED: { className: 'bg-green-50 text-green-800', label: 'Resolved' },
  REJECTED: { className: 'bg-red-50 text-red-800', label: 'Rejected' },
  DUPLICATE: { className: 'bg-ink-100 text-ink-600', label: 'Duplicate' },
  INSUFFICIENT_EVIDENCE: { className: 'bg-red-50 text-red-800', label: 'Needs evidence' },
  OUTSIDE_JURISDICTION: { className: 'bg-ink-100 text-ink-600', label: 'Outside jurisdiction' },
  ALREADY_RESOLVED: { className: 'bg-green-50 text-green-800', label: 'Already resolved' },
};

export function StatusBadge({
  status,
  label,
}: {
  status: ProblemStatus | string;
  label?: string;
}) {
  const style = STATUS_STYLES[status] ?? { className: 'bg-ink-100 text-ink-700', label: status };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${style.className}`}
    >
      {label ?? style.label}
    </span>
  );
}

const PRIORITY_STYLES: Record<string, string> = {
  LOW: 'bg-ink-100 text-ink-600',
  MEDIUM: 'bg-ink-100 text-ink-700',
  HIGH: 'bg-orange-50 text-orange-800',
  CRITICAL: 'bg-red-50 text-red-800',
};

export function PriorityBadge({ priority, label }: { priority: string; label?: string }) {
  if (priority === 'LOW' || priority === 'MEDIUM') return null;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${PRIORITY_STYLES[priority] ?? ''}`}
    >
      {label ?? priority}
    </span>
  );
}

export function EvidenceBadge({ state }: { state: VerificationState }) {
  if (state === 'VERIFIED') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">
        <CheckIcon />
        Verified evidence
      </span>
    );
  }
  if (state === 'REJECTED') {
    return (
      <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-800">
        Evidence rejected
      </span>
    );
  }
  // The honest default. Anything uploaded is unverified until a person says
  // otherwise, and the label says exactly that.
  return (
    <span className="inline-flex items-center rounded-full bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-600">
      {state === 'UNDER_VERIFICATION' ? 'Being verified' : 'Uploaded, not verified'}
    </span>
  );
}

export function VerifiedProfessionalBadge({ badge }: { badge: string | null }) {
  if (!badge) return null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-800"
      title="JanDrishti has verified this professional claim. It is not an endorsement of any particular statement."
    >
      <CheckIcon />
      {badge}
    </span>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2.5 6.5L4.5 8.5L9.5 3.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
