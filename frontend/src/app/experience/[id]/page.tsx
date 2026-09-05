import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { StatusBadge, VerifiedProfessionalBadge } from '@/components/ui/StatusBadge';
import { CommentThread } from '@/features/comments/CommentThread';
import { ExperienceSupportButton } from '@/features/experience/ExperienceSupportButton';
import { FollowButton, ShareButton } from '@/features/problems/ProblemActions';
import { formatCount, formatDate } from '@/lib/format';
import { fetchPublic } from '@/services/api-client';
import type { ExperienceDetail } from '@/types/api';

export const revalidate = 60;

interface PageProps {
  params: Promise<{ id: string }>;
}

async function loadExperience(id: string) {
  return fetchPublic<ExperienceDetail | null>(`/experiences/${id}/`, null, 60);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const experience = await loadExperience(id);
  if (!experience) return { title: 'Contribution not found' };

  return {
    title: experience.title,
    description: experience.summary,
    alternates: { canonical: `/experience/${experience.id}` },
    openGraph: {
      title: experience.title,
      description: experience.summary,
      type: 'article',
      publishedTime: experience.created_at,
      authors: experience.author ? [experience.author.display_name] : undefined,
    },
  };
}

/** The structured body from spec 22, rendered only where the author filled it in. */
const SECTIONS: Array<{ key: keyof ExperienceDetail; heading: string }> = [
  { key: 'observed_problem', heading: 'What was observed' },
  { key: 'context', heading: 'Context' },
  { key: 'root_cause', heading: 'Root cause' },
  { key: 'personal_experience', heading: 'Professional experience' },
  { key: 'recommendation', heading: 'Recommendation' },
  { key: 'implementation', heading: 'How it could be implemented' },
  { key: 'expected_impact', heading: 'Expected impact' },
  { key: 'challenges', heading: 'Challenges' },
  { key: 'cost_implications', heading: 'Cost implications' },
];

export default async function ExperienceDetailPage({ params }: PageProps) {
  const { id } = await params;
  const experience = await loadExperience(id);
  if (!experience) notFound();

  const author = experience.author;
  const profile = author?.professional_profile;

  return (
    <article className="mx-auto max-w-content px-4 py-8 sm:px-6">
      <nav aria-label="Breadcrumb" className="text-sm text-ink-500">
        <Link href="/experience" className="hover:text-ink-800 hover:underline">
          Experience &amp; Ideas
        </Link>
      </nav>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1fr_19rem]">
        <div className="min-w-0">
          <span className="inline-flex rounded-full bg-ink-100 px-3 py-1 text-xs font-medium text-ink-700">
            {experience.type_display}
          </span>

          <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink-900">
            {experience.title}
          </h1>

          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-500">
            <span className="font-medium text-ink-800">
              {author?.display_name ?? 'Contributor'}
            </span>
            <VerifiedProfessionalBadge badge={author?.verification_badge ?? null} />
            {profile?.headline && <span>· {profile.headline}</span>}
            <span aria-hidden="true">·</span>
            <span>{formatDate(experience.created_at)}</span>
          </div>

          {profile && (
            <div className="mt-4 rounded-xl border border-ink-200 bg-white p-4 text-sm">
              <p className="text-ink-700">
                {profile.category_display}
                {profile.designation ? ` · ${profile.designation}` : ''}
                {profile.organization ? ` · ${profile.organization}` : ''}
              </p>
              {profile.years_of_experience > 0 && (
                <p className="mt-1 text-ink-500">
                  {profile.years_of_experience} years in {profile.domain_display.toLowerCase()}
                </p>
              )}
              {!author?.is_professionally_verified && (
                <p className="mt-2 text-xs text-ink-400">
                  This background is self-described and has not been verified.
                </p>
              )}
            </div>
          )}

          <div className="mt-8 space-y-8">
            {SECTIONS.map((section) => {
              const value = experience[section.key];
              if (typeof value !== 'string' || !value.trim()) return null;
              return (
                <section key={section.key}>
                  <h2 className="text-base font-semibold text-ink-900">{section.heading}</h2>
                  <p className="mt-2 whitespace-pre-line text-base leading-relaxed text-ink-700">
                    {value}
                  </p>
                </section>
              );
            })}
          </div>

          {experience.related_problems.length > 0 && (
            <section aria-labelledby="linked-heading" className="mt-10">
              <h2 id="linked-heading" className="text-lg font-semibold text-ink-900">
                Problems this addresses
              </h2>
              <ul className="mt-4 space-y-2">
                {experience.related_problems.map((problem) => (
                  <li key={problem.id}>
                    <Link
                      href={`/problems/${problem.id}`}
                      className="flex items-center gap-3 rounded-xl border border-ink-200 bg-white p-4 transition hover:border-brand-300"
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-ink-900">
                          {problem.title}
                        </span>
                        <span className="mt-0.5 block text-xs text-ink-500">
                          {formatCount(problem.support_count)} supporting
                        </span>
                      </span>
                      <StatusBadge status={problem.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="discussion-heading" className="mt-10">
            <h2 id="discussion-heading" className="text-lg font-semibold text-ink-900">
              Discussion
            </h2>
            <CommentThread targetType="EXPERIENCE" targetId={experience.id} />
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 lg:h-fit lg:space-y-4">
          <div className="rounded-xl border border-ink-200 bg-white p-5">
            <ExperienceSupportButton
              experienceId={experience.id}
              initialCount={experience.support_count}
              initiallySupported={experience.viewer_has_supported}
            />

            <dl className="mt-6 space-y-3 border-t border-ink-100 pt-5 text-sm">
              <div className="flex items-baseline justify-between">
                <dt className="text-ink-500">Comments</dt>
                <dd className="font-semibold tabular-nums text-ink-900">
                  {formatCount(experience.comment_count)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-ink-500">Linked problems</dt>
                <dd className="font-semibold tabular-nums text-ink-900">
                  {formatCount(experience.related_problem_count)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-ink-500">Credibility</dt>
                <dd className="font-semibold tabular-nums text-ink-900">
                  {Math.round(experience.credibility_score)}/100
                </dd>
              </div>
            </dl>

            <p className="mt-3 text-xs leading-relaxed text-ink-400">
              Credibility blends verification, relevance, evidence and how actionable the
              recommendation is. It is not a measure of whether the advice is correct.
            </p>

            <div className="mt-5 flex gap-2 border-t border-ink-100 pt-5">
              <FollowButton targetType="EXPERIENCE" targetId={experience.id} />
              <ShareButton title={experience.title} />
            </div>
          </div>
        </aside>
      </div>
    </article>
  );
}
