import Image from 'next/image';
import Link from 'next/link';

import type { PublicStats } from '@/types/api';

/**
 * Hero, built on `/background.png`.
 *
 * Composition notes, because the artwork constrains the layout:
 *
 * The photograph is a 2.34:1 panorama with three things already in it — a
 * six-step icon arc across the top, a figure with both arms raised dead centre,
 * and a crowd along the bottom edge. So the copy cannot go in the middle (it
 * would cover the raised arms, which are the emotional point) and cannot go
 * across the top (the arc is there).
 *
 * It goes left instead, over the skyline band, with a gradient that is strong
 * at the left edge and fully transparent by the middle. The raised figure, the
 * sunrise, the crowd and the arc all stay visible — the scrim only touches the
 * quiet part of the frame.
 */
export function HeroSection({ stats }: { stats: PublicStats }) {
  return (
    <section className="relative isolate overflow-hidden bg-brand-900">
      {/* The photograph, uncropped at the top so the arc survives. */}
      <Image
        src="/background.png"
        alt="Citizens looking out over a city at sunrise, one of them with both arms raised."
        fill
        priority
        sizes="100vw"
        className="object-cover object-center lg:object-[18%_center]"
      />

      {/* Readability scrim. Deliberately one-sided: it fades out well before
          the raised figure so nothing important sits behind a wash. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-gradient-to-r from-brand-950/45 via-brand-950/10 to-transparent"
      />

      {/* A short foot of shade so the stats bar has something to sit on. */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-brand-950/70 to-transparent"
      />

      <div className="relative mx-auto flex min-h-[70vh] max-w-content flex-col justify-end px-4 pb-8 pt-24 sm:px-6 lg:h-[860px] lg:min-h-0 lg:pb-44">
        <div className="max-w-xl rounded-3xl border border-white/15 bg-brand-950/55 p-7 shadow-2xl shadow-brand-950/30 backdrop-blur-md sm:p-9">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-saffron-300">
            See. Suggest. Solve.
          </p>

          <h1 className="mt-4 text-balance text-4xl font-bold leading-[1.05] tracking-tight text-white sm:text-5xl">
            Raise What Matters.
            <br />
            <span className="text-leaf-300">See It Move.</span>
          </h1>

          <p className="mt-5 max-w-lg text-balance text-base leading-relaxed text-brand-50">
            Report real problems, share experience and ideas, bring people together, and see
            meaningful action happen.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/report"
              className="inline-flex items-center justify-center rounded-xl bg-leaf-700 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-950/30 transition hover:-translate-y-0.5 hover:bg-leaf-800 focus:outline-none focus:ring-2 focus:ring-leaf-300 focus:ring-offset-2 focus:ring-offset-brand-900"
            >
              Raise a Problem
            </Link>
            <Link
              href="/problems"
              className="inline-flex items-center justify-center rounded-xl border border-white/70 bg-white/10 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white hover:text-brand-900 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-brand-900"
            >
              Explore Problems
            </Link>
          </div>

          <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3">
            {[
              { label: 'Real issues', dot: 'bg-saffron-400' },
              { label: 'Collective voice', dot: 'bg-white' },
              { label: 'Expert ideas', dot: 'bg-leaf-400' },
              { label: 'Visible progress', dot: 'bg-brand-200' },
            ].map((item) => (
              <li
                key={item.label}
                className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white"
              >
                <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${item.dot}`} />
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* The journey, as floating cards on the open right side of the frame.
          Hidden below xl, where they would land on top of the crowd. */}
      <StoryCards />

      <StatsBar stats={stats} />
    </section>
  );
}

/* ------------------------------------------------------------ story cards */

function StoryCards() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 hidden xl:block">
      <FloatingCard className="right-[6%] top-[52%]" delay={200}>
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <PinIcon />
        </span>
        <span>
          <span className="block text-[11px] font-semibold text-ink-400">Problem reported</span>
          <span className="block text-sm font-bold text-brand-900">Broken road · Sector 12</span>
        </span>
      </FloatingCard>

      <FloatingCard className="right-[13%] top-[64%]" delay={420}>
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-saffron-50 text-saffron-700">
          <PeopleIcon />
        </span>
        <span>
          <span className="block text-[11px] font-semibold text-ink-400">Community support</span>
          <span className="block text-sm font-bold text-brand-900">86 people face this too</span>
        </span>
      </FloatingCard>

      <FloatingCard className="right-[5%] top-[76%]" delay={640}>
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-leaf-50 text-leaf-700">
          <TickIcon />
        </span>
        <span>
          <span className="block text-[11px] font-semibold text-ink-400">Proof of work</span>
          <span className="block text-sm font-bold text-brand-900">Resolved · Verified</span>
        </span>
      </FloatingCard>
    </div>
  );
}

function FloatingCard({
  className,
  delay,
  children,
}: {
  className: string;
  delay: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`absolute flex animate-fade-up items-center gap-2.5 rounded-xl border border-white/60 bg-white/95 px-3.5 py-2.5 shadow-xl shadow-brand-950/10 backdrop-blur ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/* -------------------------------------------------------------- stats bar */

/**
 * Live figures, overlapping the foot of the image.
 *
 * Every number is an aggregate over real rows. On a deployment with no activity
 * it says so rather than showing invented totals — a civic platform that
 * inflates its own numbers has given away the only thing it is selling.
 */
function StatsBar({ stats }: { stats: PublicStats }) {
  const tiles = [
    { label: 'Citizens supporting', value: stats.citizens_supporting },
    { label: 'Problems raised', value: stats.problems_reported },
    { label: 'Ideas & experiences', value: stats.experiences_shared },
    { label: 'Government responses', value: stats.government_responses },
    { label: 'In progress / resolved', value: stats.active_problems + stats.problems_resolved },
  ];
  const isEmpty = tiles.every((tile) => tile.value === 0);

  return (
    <div className="relative px-4 pb-8 sm:px-6 lg:absolute lg:inset-x-0 lg:bottom-0 lg:px-6 lg:pb-8">
      <div className="mx-auto max-w-content rounded-2xl border border-white/60 bg-white/95 px-6 py-5 shadow-2xl shadow-brand-950/20 backdrop-blur">
        {isEmpty ? (
          <p className="text-center text-sm text-ink-500">
            No public activity on this deployment yet — these figures fill in as citizens raise
            problems and departments respond.
          </p>
        ) : (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-3 lg:grid-cols-5">
            {tiles.map((tile) => (
              <div key={tile.label} className="text-center lg:text-left">
                <dd className="text-2xl font-bold tabular-nums leading-none text-brand-900">
                  {tile.value.toLocaleString('en-IN')}
                </dd>
                <dt className="mt-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-400">
                  {tile.label}
                </dt>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ icons */

function PinIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M8 1.5c2.5 0 4.5 2 4.5 4.5 0 3.4-4.5 8-4.5 8s-4.5-4.6-4.5-8C3.5 3.5 5.5 1.5 8 1.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="6" r="1.6" fill="currentColor" />
    </svg>
  );
}

function PeopleIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" className="h-4 w-4" aria-hidden="true">
      <circle cx="6" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M1.5 13.5c0-2.5 2-4.5 4.5-4.5s4.5 2 4.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M11 3.6a2.5 2.5 0 0 1 0 4.8M14.5 13.5c0-1.6-.6-3-1.5-3.9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function TickIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" className="h-4 w-4" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5 8.2 7 10.2l4-4.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
