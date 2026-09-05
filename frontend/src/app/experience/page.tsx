import type { Metadata } from 'next';
import Link from 'next/link';

import { EmptyState, PrimaryLink } from '@/components/ui/States';
import { ExperienceCardView } from '@/features/experience/ExperienceCard';
import { fetchPublicPage } from '@/services/api-client';
import type { ExperienceCard } from '@/types/api';

export const metadata: Metadata = {
  title: 'Experience & Ideas',
  description:
    'Professional experience, root cause analysis and practical recommendations from working professionals, retired officers, domain experts and experienced citizens.',
  alternates: { canonical: '/experience' },
};

export const revalidate = 60;

const TYPE_FILTERS = [
  { value: '', label: 'All' },
  { value: 'PROFESSIONAL_EXPERIENCE', label: 'Experience' },
  { value: 'ROOT_CAUSE_ANALYSIS', label: 'Root cause' },
  { value: 'RECOMMENDATION', label: 'Recommendation' },
  { value: 'POLICY_IDEA', label: 'Policy idea' },
  { value: 'BEST_PRACTICE', label: 'Best practice' },
  { value: 'GOVERNANCE_IMPROVEMENT', label: 'Governance' },
  { value: 'COST_REDUCTION', label: 'Cost reduction' },
  { value: 'PROCESS_IMPROVEMENT', label: 'Process' },
  { value: 'TECHNOLOGY_IMPROVEMENT', label: 'Technology' },
];

const SORTS = [
  { value: 'credible', label: 'Most credible' },
  { value: 'recent', label: 'Most recent' },
  { value: 'supported', label: 'Most supported' },
  { value: 'discussed', label: 'Most discussed' },
];

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ExperiencePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const activeType = typeof params.experience_type === 'string' ? params.experience_type : '';
  const activeSort = typeof params.sort === 'string' ? params.sort : 'credible';

  const query = new URLSearchParams({ sort: activeSort, page_size: '18' });
  if (activeType) query.set('experience_type', activeType);
  if (typeof params.q === 'string' && params.q) query.set('q', params.q);
  if (typeof params.state === 'string' && params.state) query.set('state', params.state);

  const page = await fetchPublicPage<ExperienceCard>(`/experiences/?${query.toString()}`, 60);

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
            Experience &amp; Ideas
          </h1>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-500">
            What experienced people have actually seen, and what they would do about it. Open to
            working professionals, retired officers, armed forces veterans, domain experts and
            experienced citizens alike — relevant experience matters more than job title.
          </p>
        </div>
        <PrimaryLink href="/experience/new">Share an Experience</PrimaryLink>
      </header>

      <div className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-3">
        <nav aria-label="Filter by type" className="flex flex-wrap gap-1.5">
          {TYPE_FILTERS.map((filter) => {
            const isActive = filter.value === activeType;
            const linkQuery = new URLSearchParams();
            if (filter.value) linkQuery.set('experience_type', filter.value);
            if (activeSort !== 'credible') linkQuery.set('sort', activeSort);
            const href = linkQuery.toString() ? `/experience?${linkQuery}` : '/experience';
            return (
              <Link
                key={filter.value || 'all'}
                href={href}
                aria-current={isActive ? 'true' : undefined}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                  isActive
                    ? 'border-brand-600 bg-brand-50 text-brand-800'
                    : 'border-ink-200 bg-white text-ink-600 hover:bg-ink-50'
                }`}
              >
                {filter.label}
              </Link>
            );
          })}
        </nav>

        <nav aria-label="Sort" className="ml-auto flex gap-1.5">
          {SORTS.map((sort) => {
            const isActive = sort.value === activeSort;
            const linkQuery = new URLSearchParams();
            if (activeType) linkQuery.set('experience_type', activeType);
            linkQuery.set('sort', sort.value);
            return (
              <Link
                key={sort.value}
                href={`/experience?${linkQuery}`}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  isActive ? 'bg-ink-900 text-white' : 'text-ink-500 hover:bg-ink-100'
                }`}
              >
                {sort.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <p className="mt-6 rounded-lg bg-ink-100/70 px-4 py-3 text-xs leading-relaxed text-ink-600">
        Support is a signal of agreement, not proof of correctness. Contributions are ordered by a
        blend of verification, relevance, evidence and how actionable they are — not by popularity
        alone.
      </p>

      <div className="mt-6">
        {page.results.length === 0 ? (
          <EmptyState
            title="Nothing here yet"
            description="If you have spent years around a problem and know why the usual fix keeps failing, that knowledge is worth writing down."
            action={<PrimaryLink href="/experience/new">Share an experience</PrimaryLink>}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {page.results.map((experience) => (
              <ExperienceCardView key={experience.id} experience={experience} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
