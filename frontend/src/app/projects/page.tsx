import type { Metadata } from 'next';
import Link from 'next/link';

import { EmptyState } from '@/components/ui/States';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDate, formatRupees } from '@/lib/format';
import { fetchPublicPage } from '@/services/api-client';

export const metadata: Metadata = {
  title: 'Projects',
  description:
    'Work started in response to reported problems, with milestones, progress updates and published proof.',
  alternates: { canonical: '/projects' },
};

export const revalidate = 60;

interface ProjectRow {
  id: string;
  title: string;
  description: string;
  status: string;
  status_display: string;
  problem_id: string | null;
  department_name: string;
  target_amount: string;
  start_date: string | null;
  expected_end_date: string | null;
  progress_percent: number;
  update_count: number;
  state: string;
  city: string;
  created_at: string;
}

export default async function ProjectsPage() {
  const page = await fetchPublicPage<ProjectRow>('/projects/?page_size=24', 60);

  return (
    <div className="mx-auto max-w-content px-4 py-10 sm:px-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-ink-900">Projects</h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-500">
          Work started in response to reported problems. Each project publishes its milestones,
          progress and completion evidence, so a claim of completion can be checked against what
          was actually shown.
        </p>
      </header>

      <div className="mt-8">
        {page.results.length === 0 ? (
          <EmptyState
            title="No projects yet"
            description="When a department or community team starts work on a reported problem, the project and its progress appear here."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {page.results.map((project) => (
              <article
                key={project.id}
                className="flex flex-col rounded-xl border border-ink-200 bg-white p-5 transition hover:border-brand-300"
              >
                <Link href={`/projects/${project.id}`} className="flex flex-1 flex-col">
                  <StatusBadge status={project.status} label={project.status_display} />

                  <h2 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-ink-900">
                    {project.title}
                  </h2>
                  <p className="mt-2 line-clamp-2 text-sm text-ink-500">{project.description}</p>

                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-ink-500">
                      <span>Progress</span>
                      <span className="font-medium tabular-nums text-ink-800">
                        {project.progress_percent}%
                      </span>
                    </div>
                    <div
                      className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink-100"
                      role="progressbar"
                      aria-valuenow={project.progress_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${project.title} progress`}
                    >
                      <div
                        className="h-full rounded-full bg-brand-600 transition-all"
                        style={{ width: `${project.progress_percent}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-auto pt-4 text-xs text-ink-500">
                    {project.department_name && <p>{project.department_name}</p>}
                    <p className="mt-0.5">
                      {Number.parseFloat(project.target_amount) > 0 &&
                        `${formatRupees(project.target_amount)} · `}
                      {project.expected_end_date
                        ? `due ${formatDate(project.expected_end_date)}`
                        : `started ${formatDate(project.created_at)}`}
                    </p>
                  </div>
                </Link>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
