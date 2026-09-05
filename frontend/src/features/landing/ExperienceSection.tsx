import Link from 'next/link';

import { PotholeGlyph } from '@/components/illustrations/Figures';

/**
 * "Problems need more than complaints."
 *
 * The section that separates JanDrishti from a complaint portal. It has to make
 * two things obvious: that structured professional judgement is welcome here,
 * and that it is open to working *and* retired people, and to experienced
 * citizens with no title at all.
 */

const PEOPLE = [
  { role: 'Engineer', tone: 'navy' },
  { role: 'Doctor', tone: 'leaf' },
  { role: 'Teacher', tone: 'saffron' },
  { role: 'Lawyer', tone: 'navy' },
  { role: 'Government professional', tone: 'leaf' },
  { role: 'Retired professional', tone: 'saffron' },
  { role: 'Technology expert', tone: 'navy' },
  { role: 'Infrastructure expert', tone: 'leaf' },
  { role: 'Experienced citizen', tone: 'saffron' },
] as const;

const ROLE_TONES = {
  navy: 'border-brand-200 bg-brand-50 text-brand-800',
  leaf: 'border-leaf-200 bg-leaf-50 text-leaf-800',
  saffron: 'border-saffron-200 bg-saffron-50 text-saffron-800',
};

const CONTRIBUTION = [
  {
    label: 'Experience',
    body: 'Based on drainage projects I have worked on across three municipal wards.',
  },
  {
    label: 'Root cause',
    body: 'Blocked storm-water capacity — the drains silt up and were never cleared before the monsoon.',
  },
  {
    label: 'Recommendation',
    body: 'Improve drainage flow and add inspection points along the affected stretch.',
  },
  {
    label: 'Implementation',
    body: 'Desilt before June each year; publish the inspection record with the work order.',
  },
  { label: 'Expected impact', body: 'Reduce recurring waterlogging after ordinary rainfall.' },
];

export function ExperienceSection() {
  return (
    <section aria-labelledby="experience-heading" className="border-b border-ink-200 bg-brand-900">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-start lg:gap-16">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-saffron-400">
              Experience &amp; Ideas
            </p>
            <h2
              id="experience-heading"
              className="mt-3 text-balance text-3xl font-bold tracking-tight text-white sm:text-4xl"
            >
              Problems need more than complaints.
            </h2>
            <p className="mt-4 max-w-lg leading-relaxed text-brand-100">
              Share your professional experience, practical knowledge and ideas to help
              communities solve real problems — and to argue what the government should actually
              do about the issues that keep coming back. Anyone who has worked near a problem long
              enough to know why the usual fix keeps failing has something worth writing down.
            </p>

            <ul className="mt-8 flex flex-wrap gap-2">
              {PEOPLE.map((person) => (
                <li
                  key={person.role}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${ROLE_TONES[person.tone]}`}
                >
                  {person.role}
                </li>
              ))}
            </ul>

            <p className="mt-6 text-sm leading-relaxed text-brand-200">
              Open to working professionals, retired professionals and experienced citizens
              alike. Relevant experience matters more than employment status.
            </p>

            <Link
              href="/experience/new"
              className="mt-8 inline-flex items-center justify-center rounded-xl bg-white px-7 py-3.5 text-sm font-semibold text-brand-900 transition hover:-translate-y-0.5 hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-brand-900"
            >
              Share Your Experience
            </Link>
          </div>

          {/* A professional annotating a real problem. */}
          <div className="rounded-2xl border border-brand-700 bg-brand-800/60 p-5 backdrop-blur sm:p-7">
            <div className="flex items-center gap-3 rounded-xl bg-brand-950/40 p-3">
              <span
                aria-hidden="true"
                className="flex h-12 w-14 shrink-0 items-end justify-center overflow-hidden rounded-lg bg-brand-100"
              >
                <PotholeGlyph className="h-10 w-10" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  Frequent flooding in this area
                </p>
                <p className="text-xs text-brand-300">Reported by 86 people · Sector 12</p>
              </div>
            </div>

            <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-saffron-400">
              A professional adds
            </p>

            <dl className="mt-3 space-y-3">
              {CONTRIBUTION.map((item) => (
                <div key={item.label} className="rounded-xl bg-white/95 p-3.5">
                  <dt className="text-[11px] font-bold uppercase tracking-wide text-brand-600">
                    {item.label}
                  </dt>
                  <dd className="mt-1 text-sm leading-relaxed text-ink-700">{item.body}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </section>
  );
}
