import Link from 'next/link';

import { RaisedHandsFigure, StandingFigure } from '@/components/illustrations/Figures';

/**
 * The closing section.
 *
 * The page ends on the same image it opened with — one person with their hands
 * up, and others standing with them — because that is the whole argument.
 * Everything between the two is the mechanism.
 */
export function FinalCta() {
  return (
    <section id="join" className="relative overflow-hidden bg-brand-900 scroll-mt-24">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-80 bg-[radial-gradient(60%_100%_at_50%_100%,rgba(237,106,8,0.26),transparent_70%)]"
      />

      <div className="relative mx-auto max-w-content px-4 pt-20 sm:px-6">
        <div className="mx-auto max-w-3xl text-center">
          {/* The line that says whose problem this is. Set above the headline
              rather than inside it, so it reads as the premise and not the ask. */}
          <p className="text-balance text-xl font-semibold tracking-tight text-saffron-300 sm:text-2xl">
            It&rsquo;s our India. Let&rsquo;s improve it — together.
          </p>

          <h2 className="mt-4 text-balance text-3xl font-bold leading-[1.1] tracking-tight text-white sm:text-4xl lg:text-5xl">
            Your voice can start
            <br />
            <span className="text-saffron-400">the change.</span>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-balance text-lg leading-relaxed text-brand-100">
            See a problem. Share your experience. Suggest an idea. Help move it forward.
          </p>

          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/report"
              className="inline-flex w-full items-center justify-center rounded-xl bg-saffron-500 px-8 py-4 text-sm font-semibold text-brand-950 shadow-lg shadow-saffron-500/25 transition hover:-translate-y-0.5 hover:bg-saffron-400 focus:outline-none focus:ring-2 focus:ring-saffron-300 focus:ring-offset-2 focus:ring-offset-brand-900 sm:w-auto"
            >
              Raise a Problem
            </Link>
            <Link
              href="/experience/new"
              className="inline-flex w-full items-center justify-center rounded-xl border border-brand-600 px-8 py-4 text-sm font-semibold text-white transition hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-brand-900 sm:w-auto"
            >
              Share an Experience
            </Link>
          </div>

          <p className="mt-8 text-xs text-brand-300">
            Browsing needs no account. Signing in is only for taking part.
          </p>
        </div>

        {/* The crowd, standing on the section's baseline. */}
        <div
          className="mt-14 flex items-end justify-center gap-1 sm:gap-2"
          aria-hidden="true"
        >
          <StandingFigure tone="slate" className="h-16 w-auto opacity-40 sm:h-20" />
          <StandingFigure tone="sky" className="h-20 w-auto opacity-60 sm:h-24" />
          <StandingFigure tone="leaf" className="h-24 w-auto opacity-80 sm:h-28" />
          <RaisedHandsFigure tone="saffron" className="h-32 w-auto sm:h-40" />
          <StandingFigure tone="navy" className="h-24 w-auto opacity-80 sm:h-28" />
          <StandingFigure tone="sky" className="h-20 w-auto opacity-60 sm:h-24" />
          <StandingFigure tone="slate" className="h-16 w-auto opacity-40 sm:h-20" />
        </div>

        <p className="pb-10 text-center text-[11px] font-semibold uppercase tracking-[0.22em] text-brand-400">
          One person raises it · A community makes it visible · Proof makes it trustworthy
        </p>
      </div>
    </section>
  );
}
