/**
 * Problem detail (spec 14).
 *
 * Public, server-rendered, and shareable: the metadata is generated per problem
 * so a link posted anywhere carries its real title, location and status.
 */
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { EvidenceBadge, PriorityBadge, StatusBadge } from '@/components/ui/StatusBadge';
import { CommentThread } from '@/features/comments/CommentThread';
import { ExperienceCardView } from '@/features/experience/ExperienceCard';
import { ProblemTimeline } from '@/features/problems/ProblemTimeline';
import { SupportButton } from '@/features/problems/SupportButton';
import { FollowButton, ShareButton } from '@/features/problems/ProblemActions';
import { formatCount, formatDate, formatDateTime } from '@/lib/format';
import { fetchPublic } from '@/services/api-client';
import type { ExperienceCard, ProblemDetail } from '@/types/api';

export const revalidate = 30;

interface PageProps {
  params: Promise<{ id: string }>;
}

async function loadProblem(id: string): Promise<ProblemDetail | null> {
  return fetchPublic<ProblemDetail | null>(`/problems/${id}/`, null, 30);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const problem = await loadProblem(id);
  if (!problem) return { title: 'Problem not found' };

  const location = problem.location.display || 'India';
  const description = `${problem.description.slice(0, 155)}…`;

  return {
    title: problem.title,
    description,
    alternates: { canonical: `/problems/${problem.id}` },
    openGraph: {
      title: `${problem.title} — ${location}`,
      description,
      type: 'article',
      publishedTime: problem.created_at,
      images: problem.cover_image ? [{ url: problem.cover_image.url }] : undefined,
    },
    twitter: {
      card: problem.cover_image ? 'summary_large_image' : 'summary',
      title: problem.title,
      description,
    },
  };
}

export default async function ProblemDetailPage({ params }: PageProps) {
  const { id } = await params;
  const problem = await loadProblem(id);
  if (!problem) notFound();

  const relatedExperiences = await fetchPublic<ExperienceCard[]>(
    `/experiences/for-problem/${problem.id}/`,
    [],
  );

  return (
    <article className="mx-auto max-w-content px-4 py-8 sm:px-6">
      {/* Structured data so a search engine understands what this page is. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Report',
            headline: problem.title,
            description: problem.description.slice(0, 300),
            datePublished: problem.created_at,
            dateModified: problem.last_activity_at,
            contentLocation: {
              '@type': 'Place',
              address: {
                '@type': 'PostalAddress',
                addressLocality: problem.location.city,
                addressRegion: problem.location.state,
                addressCountry: 'IN',
              },
            },
          }),
        }}
      />

      <nav aria-label="Breadcrumb" className="text-sm text-ink-500">
        <Link href="/problems" className="hover:text-ink-800 hover:underline">
          Problems
        </Link>
        {problem.category && (
          <>
            <span aria-hidden="true" className="mx-2">
              /
            </span>
            <Link
              href={`/problems?category=${problem.category.id}`}
              className="hover:text-ink-800 hover:underline"
            >
              {problem.category.name}
            </Link>
          </>
        )}
      </nav>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={problem.status} label={problem.status_display} />
            <PriorityBadge priority={problem.priority} label={problem.priority_display} />
            {problem.report_count > 1 && (
              <span className="rounded-full bg-ink-100 px-2.5 py-1 text-xs font-medium text-ink-700">
                Reported by {formatCount(problem.report_count)} people
              </span>
            )}
          </div>

          <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink-900">
            {problem.title}
          </h1>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-500">
            <span>{problem.location.display || 'Location not specified'}</span>
            <span aria-hidden="true">·</span>
            <span>Reported {formatDate(problem.created_at)}</span>
            <span aria-hidden="true">·</span>
            <span>by {problem.reporter.display_name}</span>
            {problem.department && (
              <>
                <span aria-hidden="true">·</span>
                <span className="font-medium text-ink-700">{problem.department.name}</span>
              </>
            )}
          </div>

          {problem.cluster && (
            <Link
              href={`/clusters/${problem.cluster.id}`}
              className="mt-5 flex items-start gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4 transition hover:bg-brand-100"
            >
              <span aria-hidden="true" className="text-lg">
                🔗
              </span>
              <span className="text-sm">
                <strong className="font-semibold text-brand-900">
                  Grouped with {problem.cluster.problem_count - 1} similar report
                  {problem.cluster.problem_count === 2 ? '' : 's'}
                </strong>
                <span className="mt-0.5 block text-brand-800">
                  Every original report is preserved. Together they carry{' '}
                  {formatCount(problem.cluster.total_support)} supporters. See all reports →
                </span>
              </span>
            </Link>
          )}

          <div className="mt-6 whitespace-pre-line text-base leading-relaxed text-ink-700">
            {problem.description}
          </div>

          {problem.media.length > 0 && <EvidenceGallery problem={problem} />}

          {problem.government_responses.length > 0 && (
            <section aria-labelledby="responses-heading" className="mt-10">
              <h2 id="responses-heading" className="text-lg font-semibold text-ink-900">
                Government responses
              </h2>
              <div className="mt-4 space-y-4">
                {problem.government_responses.map((response) => (
                  <div
                    key={response.id}
                    className="rounded-xl border border-ink-200 bg-white p-5"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800">
                        {response.kind_display}
                      </span>
                      <span className="font-medium text-ink-800">
                        {response.department_name || 'Government'}
                      </span>
                      <span className="ml-auto text-xs text-ink-400">
                        {formatDateTime(response.created_at)}
                      </span>
                    </div>
                    <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-ink-700">
                      {response.message}
                    </p>
                    {response.expected_resolution_date && (
                      <p className="mt-3 text-sm text-ink-500">
                        Expected resolution:{' '}
                        <strong className="font-medium text-ink-800">
                          {formatDate(response.expected_resolution_date)}
                        </strong>
                      </p>
                    )}
                    {response.reference_number && (
                      <p className="mt-1 text-xs text-ink-400">
                        Reference: {response.reference_number}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          <section aria-labelledby="timeline-heading" className="mt-10">
            <h2 id="timeline-heading" className="text-lg font-semibold text-ink-900">
              Progress and proof
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              A permanent public record of what has happened to this issue.
            </p>
            <ProblemTimeline events={problem.timeline} />
          </section>

          {relatedExperiences.length > 0 && (
            <section aria-labelledby="related-experience-heading" className="mt-10">
              <h2 id="related-experience-heading" className="text-lg font-semibold text-ink-900">
                What experienced people say
              </h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {relatedExperiences.map((experience) => (
                  <ExperienceCardView key={experience.id} experience={experience} />
                ))}
              </div>
            </section>
          )}

          <section aria-labelledby="discussion-heading" className="mt-10">
            <h2 id="discussion-heading" className="text-lg font-semibold text-ink-900">
              Discussion
            </h2>
            <CommentThread targetType="PROBLEM" targetId={problem.id} />
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 lg:h-fit lg:space-y-4">
          <div className="rounded-xl border border-ink-200 bg-white p-5">
            <SupportButton
              problemId={problem.id}
              initialCount={problem.support_count}
              initiallySupported={problem.viewer_has_supported}
              title={problem.title}
            />

            <dl className="mt-6 space-y-3 border-t border-ink-100 pt-5 text-sm">
              <Stat label="People affected" value={formatCount(problem.support_count)} />
              <Stat label="Independent reports" value={formatCount(problem.report_count)} />
              <Stat label="Evidence files" value={formatCount(problem.evidence_count)} />
              <Stat
                label={problem.resolved_at ? 'Days to resolve' : 'Days open'}
                value={formatCount(problem.days_open)}
              />
            </dl>

            <div className="mt-5 flex gap-2 border-t border-ink-100 pt-5">
              <FollowButton targetType="PROBLEM" targetId={problem.id} />
              <ShareButton title={problem.title} />
            </div>
          </div>

          {problem.location.latitude !== null && problem.location.longitude !== null && (
            <div className="rounded-xl border border-ink-200 bg-white p-5">
              <h2 className="text-sm font-semibold text-ink-900">Location</h2>
              <p className="mt-1 text-sm text-ink-500">{problem.location.display}</p>
              <a
                href={`https://www.openstreetmap.org/?mlat=${problem.location.latitude}&mlon=${problem.location.longitude}#map=17/${problem.location.latitude}/${problem.location.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-block text-sm font-medium text-brand-700 hover:underline"
              >
                Open in map →
              </a>
            </div>
          )}

          {problem.closure_reason && (
            <div className="rounded-xl border border-ink-200 bg-ink-50 p-5">
              <h2 className="text-sm font-semibold text-ink-900">Why this was closed</h2>
              <p className="mt-1.5 text-sm text-ink-600">{problem.closure_reason}</p>
            </div>
          )}
        </aside>
      </div>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="font-semibold tabular-nums text-ink-900">{value}</dd>
    </div>
  );
}

function EvidenceGallery({ problem }: { problem: ProblemDetail }) {
  const groups = [
    { purpose: 'BEFORE', label: 'Before' },
    { purpose: 'DURING', label: 'During work' },
    { purpose: 'AFTER', label: 'After' },
  ] as const;

  const hasProofSequence = groups.some((group) =>
    problem.media.some((item) => item.purpose === group.purpose),
  );
  const general = problem.media.filter(
    (item) => !groups.some((group) => group.purpose === item.purpose),
  );

  return (
    <section aria-labelledby="evidence-heading" className="mt-8">
      <h2 id="evidence-heading" className="text-lg font-semibold text-ink-900">
        Evidence
      </h2>
      <p className="mt-1 text-sm text-ink-500">
        Files uploaded by citizens and officials. Anything not marked verified has not been
        independently checked.
      </p>

      {hasProofSequence && (
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {groups.map((group) => {
            const items = problem.media.filter((item) => item.purpose === group.purpose);
            if (items.length === 0) return null;
            return (
              <div key={group.purpose}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                  {group.label}
                </p>
                <div className="space-y-2">
                  {items.map((item) => (
                    <MediaTile key={item.id} item={item} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {general.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {general.map((item) => (
            <MediaTile key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

function MediaTile({ item }: { item: ProblemDetail['media'][number] }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-ink-200 bg-white">
      {item.media_type === 'IMAGE' ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.thumbnail_url || item.url}
          alt={item.caption || 'Evidence photograph'}
          loading="lazy"
          className="aspect-[4/3] w-full object-cover"
        />
      ) : (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex aspect-[4/3] items-center justify-center bg-ink-50 text-sm font-medium text-brand-700 hover:underline"
        >
          {item.media_type === 'VIDEO' ? 'Play video' : 'Open document'}
        </a>
      )}
      <figcaption className="space-y-1 p-2">
        <EvidenceBadge state={item.verification_status} />
        {item.caption && <p className="text-xs text-ink-500">{item.caption}</p>}
      </figcaption>
    </figure>
  );
}
