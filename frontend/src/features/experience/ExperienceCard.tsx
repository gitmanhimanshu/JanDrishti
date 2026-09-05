import Link from 'next/link';

import { VerifiedProfessionalBadge } from '@/components/ui/StatusBadge';
import { formatRelative } from '@/lib/format';
import type { ExperienceCard } from '@/types/api';

export function ExperienceCardView({ experience }: { experience: ExperienceCard }) {
  const author = experience.author;
  const profile = author?.professional_profile;

  return (
    <article className="group flex h-full flex-col rounded-xl border border-ink-200 bg-white p-5 transition hover:border-brand-300 hover:shadow-sm">
      <Link href={`/experience/${experience.id}`} className="flex flex-1 flex-col focus:outline-none">
        <span className="inline-flex w-fit rounded-full bg-ink-100 px-2.5 py-1 text-xs font-medium text-ink-700">
          {experience.type_display}
        </span>

        <h3 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-ink-900 group-hover:text-brand-800">
          {experience.title}
        </h3>

        <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-500">
          {experience.summary}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
          <span className="font-medium text-ink-800">{author?.display_name ?? 'Contributor'}</span>
          <VerifiedProfessionalBadge badge={author?.verification_badge ?? null} />
          {profile?.headline && (
            <span className="truncate text-ink-400">· {profile.headline}</span>
          )}
        </div>

        <div className="mt-auto flex items-center gap-4 pt-4 text-xs text-ink-500">
          <span>{experience.support_count.toLocaleString('en-IN')} supporting</span>
          <span>{experience.comment_count} comments</span>
          {experience.related_problem_count > 0 && (
            <span className="text-brand-700">
              {experience.related_problem_count} linked problem
              {experience.related_problem_count === 1 ? '' : 's'}
            </span>
          )}
          <span className="ml-auto shrink-0">{formatRelative(experience.created_at)}</span>
        </div>
      </Link>
    </article>
  );
}
