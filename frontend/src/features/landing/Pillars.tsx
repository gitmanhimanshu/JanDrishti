import { AvatarDot, CheckGlyph } from '@/components/illustrations/Figures';

/**
 * "Why JanDrishti" — four pillars, short copy.
 *
 * Each pillar is one promise the platform actually keeps in code, not a value
 * statement: visibility, evidence, collective weight, proof.
 */

const PILLARS = [
  {
    title: 'People',
    copy: 'Collective voice.',
    tone: 'saffron',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="h-7 w-7" aria-hidden="true">
        <path
          d="M2 16c4-6.5 8.7-10 14-10s10 3.5 14 10c-4 6.5-8.7 10-14 10S6 22.5 2 16Z"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="16" r="4" fill="currentColor" />
      </svg>
    ),
  },
  {
    title: 'Experience',
    copy: 'Real-world knowledge.',
    tone: 'navy',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="h-7 w-7" aria-hidden="true">
        <rect x="3" y="8" width="26" height="18" rx="3" stroke="currentColor" strokeWidth="2.2" />
        <path d="M11 8l2-3h6l2 3" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
        <circle cx="16" cy="17" r="5" stroke="currentColor" strokeWidth="2.2" />
      </svg>
    ),
  },
  {
    title: 'Evidence',
    copy: 'Context and proof.',
    tone: 'navy',
    icon: (
      <span className="flex -space-x-1.5">
        <AvatarDot tone="navy" className="h-6 w-6" />
        <AvatarDot tone="sky" className="h-6 w-6" />
        <AvatarDot tone="slate" className="h-6 w-6" />
      </span>
    ),
  },
  {
    title: 'Action',
    copy: 'Visible progress.',
    tone: 'leaf',
    icon: <CheckGlyph className="h-7 w-7" />,
  },
] as const;

const TONES = {
  saffron: 'text-saffron-600 bg-saffron-50 border-saffron-100',
  navy: 'text-brand-600 bg-brand-50 border-brand-100',
  leaf: 'text-leaf-600 bg-leaf-50 border-leaf-100',
};

export function Pillars() {
  return (
    <section aria-labelledby="pillars-heading" className="border-b border-ink-200 bg-ink-50">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-500">
            Why JanDrishti
          </p>
          <h2
            id="pillars-heading"
            className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
          >
            People. Experience. Evidence. Action.
          </h2>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((pillar) => (
            <div
              key={pillar.title}
              className="rounded-2xl border border-ink-200 bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg"
            >
              <span
                className={`flex h-14 w-14 items-center justify-center rounded-xl border ${TONES[pillar.tone]}`}
              >
                {pillar.icon}
              </span>
              <h3 className="mt-5 text-lg font-bold text-brand-900">{pillar.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{pillar.copy}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
