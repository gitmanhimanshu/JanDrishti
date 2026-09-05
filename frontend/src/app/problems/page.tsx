/**
 * Problems listing (spec 13).
 *
 * Server-rendered and fully usable without an account: filters and tabs live in
 * the URL, so a filtered view is shareable, indexable and survives a refresh.
 */
import type { Metadata } from 'next';
import Link from 'next/link';

import { EmptyState, PrimaryLink } from '@/components/ui/States';
import { ProblemCardView } from '@/features/problems/ProblemCard';
import { ProblemFilters } from '@/features/problems/ProblemFilters';
import { fetchPublic, fetchPublicPage } from '@/services/api-client';
import type { Category, ProblemCard, RankingTab } from '@/types/api';

export const metadata: Metadata = {
  title: 'Problems',
  description:
    'Browse public problems reported by citizens: location, evidence, support, department and current status.',
  alternates: { canonical: '/problems' },
};

export const revalidate = 30;

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function buildQuery(params: Record<string, string | string[] | undefined>): string {
  const allowed = [
    'tab',
    'q',
    'category',
    'department',
    'state',
    'district',
    'city',
    'status',
    'priority',
    'page',
    'lat',
    'lng',
    'radius_km',
    'min_support',
  ];
  const query = new URLSearchParams();
  for (const key of allowed) {
    const value = params[key];
    if (typeof value === 'string' && value) query.set(key, value);
    else if (Array.isArray(value)) value.forEach((item) => query.append(key, item));
  }
  if (!query.has('page_size')) query.set('page_size', '18');
  return query.toString();
}

export default async function ProblemsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const activeTab = typeof params.tab === 'string' ? params.tab : 'trending';

  const [tabs, categories, page] = await Promise.all([
    fetchPublic<RankingTab[]>('/problems/tabs/', []),
    fetchPublic<Category[]>('/categories/', []),
    fetchPublicPage<ProblemCard>(`/problems/?${buildQuery(params)}`, 30),
  ]);

  const hasFilters = Boolean(params.q || params.category || params.state || params.status);

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">Problems</h1>
          <p className="mt-1.5 max-w-2xl text-sm text-ink-500">
            Public problems reported by citizens, with evidence, community support and the
            responsible department. Anyone can read; signing in is only needed to take part.
          </p>
        </div>
        <PrimaryLink href="/report">Report a Problem</PrimaryLink>
      </header>

      <nav aria-label="Sort problems" className="mt-8 -mb-px overflow-x-auto">
        <ul className="flex min-w-max gap-1 border-b border-ink-200">
          {tabs.map((tab) => {
            const isActive = tab.key === activeTab;
            const query = new URLSearchParams(buildQuery({ ...params, page: undefined }));
            query.set('tab', tab.key);
            return (
              <li key={tab.key}>
                <Link
                  href={`/problems?${query.toString()}`}
                  aria-current={isActive ? 'page' : undefined}
                  title={tab.description}
                  className={`inline-block border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                    isActive
                      ? 'border-brand-600 text-brand-800'
                      : 'border-transparent text-ink-500 hover:border-ink-300 hover:text-ink-800'
                  }`}
                >
                  {tab.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-8 grid gap-8 lg:grid-cols-[16rem_1fr]">
        <ProblemFilters categories={categories} />

        <section aria-label="Problem results">
          {page.meta && page.results.length > 0 && (
            <p className="mb-4 text-sm text-ink-500">
              {page.meta.count.toLocaleString('en-IN')} problem
              {page.meta.count === 1 ? '' : 's'}
              {hasFilters ? ' matching your filters' : ''}
            </p>
          )}

          {page.results.length === 0 ? (
            <EmptyState
              title={hasFilters ? 'No problems match these filters' : 'No problems reported yet'}
              description={
                hasFilters
                  ? 'Try widening the location or clearing a filter. Nothing is hidden from you — there simply are no matches.'
                  : 'Nothing has been reported here yet. When a citizen reports a problem it appears immediately, with its evidence and location.'
              }
              action={
                hasFilters ? (
                  <Link
                    href="/problems"
                    className="text-sm font-semibold text-brand-700 hover:underline"
                  >
                    Clear all filters
                  </Link>
                ) : (
                  <PrimaryLink href="/report">Report a Problem</PrimaryLink>
                )
              }
            />
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {page.results.map((problem) => (
                  <ProblemCardView key={problem.id} problem={problem} />
                ))}
              </div>
              {page.meta && page.meta.total_pages > 1 && (
                <Pagination params={params} meta={page.meta} />
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Pagination({
  params,
  meta,
}: {
  params: Record<string, string | string[] | undefined>;
  meta: { page: number; total_pages: number };
}) {
  const pageLink = (page: number) => {
    const query = new URLSearchParams(buildQuery({ ...params, page: String(page) }));
    return `/problems?${query.toString()}`;
  };

  return (
    <nav aria-label="Pagination" className="mt-10 flex items-center justify-between gap-4">
      {meta.page > 1 ? (
        <Link
          href={pageLink(meta.page - 1)}
          className="rounded-lg border border-ink-300 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50"
        >
          ← Previous
        </Link>
      ) : (
        <span />
      )}
      <span className="text-sm text-ink-500">
        Page {meta.page} of {meta.total_pages}
      </span>
      {meta.page < meta.total_pages ? (
        <Link
          href={pageLink(meta.page + 1)}
          className="rounded-lg border border-ink-300 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50"
        >
          Next →
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
