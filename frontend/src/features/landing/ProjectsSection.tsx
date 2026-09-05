import Link from 'next/link';

import { formatRupees } from '@/lib/format';

/**
 * "From problems to projects."
 *
 * The step most civic platforms skip: a problem that gets acted on becomes a
 * piece of work with a budget, milestones and a completion claim that can be
 * checked. The figures below are a shaped demo — the real ones come from
 * /api/v1/projects/, and the shape here matches that response so swapping in
 * live data is a fetch, not a rewrite.
 */

interface ProjectSummary {
  title: string;
  problem: string;
  target: number;
  progress: number;
  milestonesDone: number;
  milestonesTotal: number;
  updates: number;
  proofItems: number;
  status: string;
}

/** Matches the ProjectSerializer shape so this can be replaced by an API call. */
const DEMO_PROJECT: ProjectSummary = {
  title: 'Road Repair Project — Sector 12',
  problem: 'Broken road near school',
  target: 1_000_000,
  progress: 68,
  milestonesDone: 3,
  milestonesTotal: 5,
  updates: 12,
  proofItems: 24,
  status: 'Work in progress',
};

const CHAIN = ['Problem', 'Project', 'Milestones', 'Progress', 'Proof'];

export function ProjectsSection() {
  const project = DEMO_PROJECT;

  return (
    <section aria-labelledby="projects-heading" className="border-b border-ink-200 bg-ink-50">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:gap-16">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-leaf-600">
              Projects
            </p>
            <h2
              id="projects-heading"
              className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
            >
              From problems to projects
            </h2>
            <p className="mt-4 max-w-md leading-relaxed text-ink-600">
              When a problem is acted on, it becomes a piece of work with a budget, milestones and
              a public record. Anyone can follow it — no account, no request, no waiting.
            </p>

            {/* The chain, as a compact flow. */}
            <ol className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-2">
              {CHAIN.map((step, index) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs font-semibold text-brand-900">
                    {step}
                  </span>
                  {index < CHAIN.length - 1 && (
                    <span aria-hidden="true" className="text-ink-300">
                      →
                    </span>
                  )}
                </li>
              ))}
            </ol>

            <Link
              href="/projects"
              className="mt-8 inline-flex items-center rounded-xl border border-ink-300 bg-white px-6 py-3 text-sm font-semibold text-brand-900 transition hover:border-brand-300 hover:bg-brand-50"
            >
              Browse projects →
            </Link>
          </div>

          {/* The project card. */}
          <div className="overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-ink-100 p-6">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">
                  From: {project.problem}
                </p>
                <h3 className="mt-1.5 text-lg font-bold text-brand-900">{project.title}</h3>
              </div>
              <span className="shrink-0 rounded-full bg-leaf-50 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-leaf-800">
                {project.status}
              </span>
            </div>

            <div className="p-6">
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-semibold text-brand-900">Progress</span>
                <span className="text-2xl font-bold tabular-nums text-leaf-700">
                  {project.progress}%
                </span>
              </div>
              <div
                role="progressbar"
                aria-valuenow={project.progress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${project.title} progress`}
                className="mt-3 h-2.5 overflow-hidden rounded-full bg-ink-100"
              >
                <div
                  className="h-full rounded-full bg-leaf-600 transition-all duration-700"
                  style={{ width: `${project.progress}%` }}
                />
              </div>

              <dl className="mt-7 grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4">
                <Figure label="Target" value={formatRupees(project.target)} />
                <Figure
                  label="Milestones"
                  value={`${project.milestonesDone} / ${project.milestonesTotal}`}
                />
                <Figure label="Updates" value={String(project.updates)} />
                <Figure label="Proof items" value={String(project.proofItems)} tone="leaf" />
              </dl>

              <p className="mt-7 rounded-xl bg-ink-50 p-4 text-xs leading-relaxed text-ink-600">
                Money figures are public for the same reason progress is: a target with no
                published spending against it is a promise, not a project.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Figure({
  label,
  value,
  tone = 'brand',
}: {
  label: string;
  value: string;
  tone?: 'brand' | 'leaf';
}) {
  return (
    <div>
      <dd
        className={`text-lg font-bold tabular-nums leading-none ${
          tone === 'leaf' ? 'text-leaf-700' : 'text-brand-900'
        }`}
      >
        {value}
      </dd>
      <dt className="mt-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-400">
        {label}
      </dt>
    </div>
  );
}
