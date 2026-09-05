import { CheckGlyph } from '@/components/illustrations/Figures';

/**
 * "This is how change starts" — the six-step journey.
 *
 * Numbered, connected, and short. Anyone should be able to follow it without
 * reading a full sentence per step, so each step is a verb, one line, and an
 * icon that means something rather than decorates.
 */

const STEPS = [
  {
    n: '1',
    title: 'See',
    copy: 'Notice something that needs attention.',
    tone: 'saffron',
    icon: <EyeIcon />,
  },
  {
    n: '2',
    title: 'Raise',
    copy: 'Report the problem with location, details and evidence.',
    tone: 'saffron',
    icon: <RaiseIcon />,
  },
  {
    n: '3',
    title: 'Support',
    copy: 'People facing the same issue can support it.',
    tone: 'navy',
    icon: <SupportIcon />,
  },
  {
    n: '4',
    title: 'Suggest',
    copy: 'Share professional experience, ideas and practical solutions.',
    tone: 'navy',
    icon: <IdeaIcon />,
  },
  {
    n: '5',
    title: 'Act',
    copy: 'Departments can acknowledge, inspect and act.',
    tone: 'leaf',
    icon: <ToolIcon />,
  },
  {
    n: '6',
    title: 'Prove',
    copy: 'Track progress and see evidence of the work completed.',
    tone: 'leaf',
    icon: <CheckGlyph className="h-6 w-6 text-leaf-600" />,
  },
] as const;

const TONES = {
  saffron: { chip: 'bg-saffron-600', ring: 'group-hover:border-saffron-300', bar: 'bg-saffron-500' },
  navy: { chip: 'bg-brand-600', ring: 'group-hover:border-brand-300', bar: 'bg-brand-500' },
  leaf: { chip: 'bg-leaf-600', ring: 'group-hover:border-leaf-300', bar: 'bg-leaf-500' },
};

export function JourneySection() {
  return (
    <section aria-labelledby="journey-heading" className="border-b border-ink-200 bg-ink-50">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-saffron-600">
            The journey
          </p>
          <h2
            id="journey-heading"
            className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
          >
            This is how change starts
          </h2>
          <p className="mt-3 text-balance leading-relaxed text-ink-500">
            Six steps, from the moment somebody notices to the moment the work can be checked.
          </p>
        </div>

        <ol className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step, index) => {
            const tone = TONES[step.tone];
            return (
              <li key={step.n} className="relative">
                <div
                  className={`group h-full rounded-2xl border border-ink-200 bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg ${tone.ring}`}
                >
                  <span aria-hidden="true" className={`block h-1 w-10 rounded-full ${tone.bar}`} />

                  <div className="mt-5 flex items-center gap-3">
                    <span
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${tone.chip}`}
                    >
                      {step.n}
                    </span>
                    <span className="flex h-8 items-center">{step.icon}</span>
                  </div>

                  <h3 className="mt-4 text-lg font-bold text-brand-900">{step.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{step.copy}</p>
                </div>

                {/* Thin thread to the next step, on wide screens only. */}
                {index < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="absolute right-[-1rem] top-1/2 hidden h-px w-4 bg-ink-200 lg:block"
                  />
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- icons */

function EyeIcon() {
  return (
    <svg viewBox="0 0 28 28" fill="none" className="h-7 w-7" aria-hidden="true">
      <path
        d="M2 14c3.5-5.5 7.5-8.5 12-8.5S22.5 8.5 26 14c-3.5 5.5-7.5 8.5-12 8.5S5.5 19.5 2 14Z"
        stroke="#ed6a08"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="14" cy="14" r="3.5" fill="#ed6a08" />
    </svg>
  );
}

function RaiseIcon() {
  return (
    <svg viewBox="0 0 28 28" fill="none" className="h-7 w-7" aria-hidden="true">
      {/* A hand raised above a line: raising something, not waving. */}
      <path
        d="M10 16V6.5a2 2 0 1 1 4 0V13m0-2.5a2 2 0 1 1 4 0V15m0-2a2 2 0 1 1 4 0v6a6 6 0 0 1-6 6h-2.6a5 5 0 0 1-3.8-1.8L6 19"
        stroke="#ed6a08"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SupportIcon() {
  return (
    <svg viewBox="0 0 28 28" fill="none" className="h-7 w-7" aria-hidden="true">
      {/* Three people, one behind the others. */}
      <circle cx="11" cy="9" r="4" stroke="#034f93" strokeWidth="2" />
      <path d="M4 23c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke="#034f93" strokeWidth="2" strokeLinecap="round" />
      <path d="M19 6.5a4 4 0 0 1 0 7.6M21 23c0-2.6-.9-4.6-2.2-6" stroke="#5089bd" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function IdeaIcon() {
  return (
    <svg viewBox="0 0 28 28" fill="none" className="h-7 w-7" aria-hidden="true">
      {/* Layered document rather than a lightbulb: this is written knowledge. */}
      <rect x="5" y="3" width="15" height="19" rx="2.5" stroke="#034f93" strokeWidth="2" />
      <path d="M9 9h7M9 13h7M9 17h4" stroke="#034f93" strokeWidth="2" strokeLinecap="round" />
      <path d="M23 8v14a2.5 2.5 0 0 1-2.5 2.5H10" stroke="#5089bd" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ToolIcon() {
  return (
    <svg viewBox="0 0 28 28" fill="none" className="h-7 w-7" aria-hidden="true">
      <path
        d="M17.5 3.5a6 6 0 0 0-7.3 7.6L3.5 17.8a2.5 2.5 0 0 0 3.5 3.5l6.7-6.7a6 6 0 0 0 7.6-7.3l-3.4 3.4-3.2-.6-.6-3.2 3.4-3.4Z"
        stroke="#247032"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="6" cy="19" r="1.4" fill="#247032" />
    </svg>
  );
}
