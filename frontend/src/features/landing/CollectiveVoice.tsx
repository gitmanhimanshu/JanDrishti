import { AvatarDot, CheckGlyph, RaisedHandsFigure } from '@/components/illustrations/Figures';

/**
 * "One report can become a collective voice."
 *
 * The clustering model, shown rather than explained: separate reports about the
 * same thing converge into one issue a department can act on, without any of
 * the originals being thrown away.
 *
 * The escalation ladder on the right is the platform's actual lifecycle, so
 * what a visitor sees here is what they will meet on a real problem page.
 */

const LADDER = [
  { label: '1 report', detail: 'A citizen raises it', tone: 'saffron', weight: 'start' },
  { label: '86 people support', detail: '"I face this too"', tone: 'saffron', weight: 'mid' },
  { label: '12 similar reports', detail: 'Filed independently', tone: 'navy', weight: 'mid' },
  { label: 'Issue cluster created', detail: 'One work item, all reports kept', tone: 'navy', weight: 'mid' },
  { label: 'Department assigned', detail: 'Routed by category and area', tone: 'navy', weight: 'mid' },
  { label: 'Inspection', detail: 'Officials visit and record', tone: 'leaf', weight: 'mid' },
  { label: 'Repair started', detail: 'Work begins, updates published', tone: 'leaf', weight: 'mid' },
  { label: 'Resolved', detail: 'With before and after proof', tone: 'leaf', weight: 'end' },
] as const;

const DOT_TONES = {
  saffron: 'bg-saffron-500',
  navy: 'bg-brand-500',
  leaf: 'bg-leaf-600',
};

export function CollectiveVoice() {
  return (
    <section aria-labelledby="collective-heading" className="border-b border-ink-200 bg-white">
      <div className="mx-auto grid max-w-content gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-500">
            Collective signal
          </p>
          <h2
            id="collective-heading"
            className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
          >
            One voice can become many
          </h2>
          <p className="mt-4 max-w-lg leading-relaxed text-ink-600">
            JanDrishti turns individual experiences into a civic signal. One report is easy to
            set aside. Eighty-six people describing the same broken road, each with their own
            evidence, is not.
          </p>

          <ConvergenceVisual />

          <p className="mt-8 rounded-xl border border-ink-200 bg-ink-50 p-4 text-sm leading-relaxed text-ink-600">
            <strong className="font-semibold text-brand-900">Nothing gets thrown away.</strong>{' '}
            Grouping gives the department one work item to act on, while every original report
            keeps its own author, evidence and timeline.
          </p>
        </div>

        {/* The ladder. */}
        <div className="relative rounded-2xl border border-ink-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="mb-6 border-b border-ink-100 pb-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">
              Example issue
            </p>
            <p className="mt-1 text-lg font-bold text-brand-900">Broken road near school</p>
          </div>

          <ol className="relative space-y-5">
            {/* One continuous rail behind the markers. */}
            <span
              aria-hidden="true"
              className="absolute bottom-3 left-[7px] top-3 w-px bg-ink-200"
            />
            {LADDER.map((rung) => (
              <li key={rung.label} className="relative flex gap-4 pl-0">
                <span
                  aria-hidden="true"
                  className={`relative z-10 mt-1 flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full ring-4 ring-white ${DOT_TONES[rung.tone]}`}
                >
                  {rung.weight === 'end' && <CheckGlyph className="h-2.5 w-2.5 text-white" />}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-brand-900">{rung.label}</span>
                  <span className="mt-0.5 block text-xs text-ink-500">{rung.detail}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/**
 * Scattered citizens converging on a single raised issue.
 *
 * Two rows funnelling inward toward one figure — the visual shape of a cluster.
 */
function ConvergenceVisual() {
  const tones = ['slate', 'sky', 'leaf', 'navy', 'slate', 'sky', 'navy'] as const;

  return (
    <div className="mt-10">
      <div className="flex flex-wrap items-center gap-1.5">
        {tones.map((tone, index) => (
          <AvatarDot key={index} tone={tone} className="h-9 w-9" />
        ))}
        <span className="ml-1 text-sm font-semibold text-ink-500">and 40 more</span>
      </div>

      {/* Funnel lines, drawn wide-to-narrow. */}
      <svg
        viewBox="0 0 320 44"
        preserveAspectRatio="none"
        className="mt-1 h-11 w-full max-w-sm"
        aria-hidden="true"
      >
        {[10, 60, 110, 160, 210, 260, 310].map((x) => (
          <path
            key={x}
            d={`M${x} 2 C ${x} 24, 160 20, 160 42`}
            stroke="#d9dadc"
            strokeWidth="1.5"
            fill="none"
          />
        ))}
      </svg>

      <div className="flex items-center gap-3">
        <RaisedHandsFigure tone="saffron" className="h-16 w-auto" />
        <span className="rounded-xl border border-saffron-200 bg-saffron-50 px-3.5 py-2">
          <span className="block text-[11px] font-semibold uppercase tracking-wide text-saffron-700">
            One issue
          </span>
          <span className="block text-sm font-bold text-brand-900">86 people affected</span>
        </span>
      </div>
    </div>
  );
}
