import { CheckGlyph } from '@/components/illustrations/Figures';

/**
 * "Transparent action" — the public progress dashboard.
 *
 * The argument of this section is one line: do not tell people something was
 * fixed, show them. So the layout gives the evidence strip as much room as the
 * timeline, and the completed step stays visibly unticked until there is proof.
 */

const TIMELINE = [
  { label: 'Reported', state: 'done', when: '12 Feb' },
  { label: 'Acknowledged', state: 'done', when: '14 Feb' },
  { label: 'Inspection', state: 'done', when: '19 Feb' },
  { label: 'Work started', state: 'done', when: '02 Mar' },
  { label: 'Work in progress', state: 'active', when: 'Now' },
  { label: 'Completed', state: 'todo', when: '—' },
] as const;

export function TransparentAction() {
  return (
    <section aria-labelledby="transparent-heading" className="border-b border-ink-200 bg-ink-50">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-leaf-600">
            Proof of work
          </p>
          <h2
            id="transparent-heading"
            className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
          >
            Don&rsquo;t just say it was fixed. Show it.
          </h2>
          <p className="mt-3 text-balance leading-relaxed text-ink-500">
            Every project publishes its milestones, its updates and its evidence — so a claim of
            completion can be checked against what was actually shown.
          </p>
        </div>

        <div className="mt-14 overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-100 px-6 py-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">
                Project
              </p>
              <p className="mt-1 text-lg font-bold text-brand-900">Road Repair — Sector 12</p>
            </div>
            <span className="rounded-full bg-leaf-50 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-leaf-800">
              Work in progress
            </span>
          </div>

          <div className="grid gap-8 p-6 lg:grid-cols-[1.1fr_1fr] lg:gap-12 lg:p-8">
            <div>
              {/* Progress */}
              <div>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-semibold text-brand-900">Progress</span>
                  <span className="text-2xl font-bold tabular-nums text-leaf-700">80%</span>
                </div>
                <div
                  role="progressbar"
                  aria-valuenow={80}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Road Repair, Sector 12 progress"
                  className="mt-3 h-2.5 overflow-hidden rounded-full bg-ink-100"
                >
                  <div className="h-full w-4/5 rounded-full bg-leaf-600" />
                </div>
              </div>

              {/* Timeline */}
              <ol className="mt-8">
                {TIMELINE.map((step, index) => (
                  <li key={step.label} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <span
                        aria-hidden="true"
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                          step.state === 'done'
                            ? 'bg-leaf-600 text-white'
                            : step.state === 'active'
                              ? 'border-2 border-leaf-600 bg-white'
                              : 'border-2 border-ink-200 bg-white'
                        }`}
                      >
                        {step.state === 'done' && <CheckGlyph className="h-3.5 w-3.5" />}
                        {step.state === 'active' && (
                          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-leaf-600" />
                        )}
                      </span>
                      {index < TIMELINE.length - 1 && (
                        <span
                          aria-hidden="true"
                          className={`my-1 w-px flex-1 ${
                            step.state === 'done' ? 'bg-leaf-200' : 'bg-ink-200'
                          }`}
                        />
                      )}
                    </div>
                    <div className="flex flex-1 items-start justify-between pb-5">
                      <span
                        className={`text-sm ${
                          step.state === 'todo'
                            ? 'text-ink-400'
                            : 'font-semibold text-brand-900'
                        }`}
                      >
                        {step.label}
                      </span>
                      <span className="text-xs tabular-nums text-ink-400">{step.when}</span>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            <div>
              {/* Evidence */}
              <p className="text-sm font-semibold text-brand-900">Evidence</p>
              <div className="mt-3 grid grid-cols-3 gap-3">
                {[
                  { label: 'Before', tone: 'bg-ink-100', ready: true },
                  { label: 'During', tone: 'bg-ink-100', ready: true },
                  { label: 'After', tone: 'bg-ink-50', ready: false },
                ].map((shot) => (
                  <figure key={shot.label}>
                    <div
                      aria-hidden="true"
                      className={`flex h-24 items-center justify-center rounded-lg border ${
                        shot.ready ? 'border-ink-200' : 'border-dashed border-ink-300'
                      } ${shot.tone}`}
                    >
                      {!shot.ready && (
                        <span className="text-[10px] font-medium text-ink-400">Pending</span>
                      )}
                    </div>
                    <figcaption className="mt-1.5 text-center text-[11px] font-medium text-ink-500">
                      {shot.label}
                    </figcaption>
                  </figure>
                ))}
              </div>

              {/* Government response */}
              <div className="mt-6 rounded-xl border border-ink-200 bg-ink-50 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-600">
                  Department response
                </p>
                <p className="mt-2 text-sm leading-relaxed text-ink-700">
                  Milling completed on the western stretch. Resurfacing scheduled for next week,
                  subject to weather.
                </p>
                <p className="mt-2 text-xs text-ink-400">Road Department · 08 Mar</p>
              </div>

              <div className="mt-4 rounded-xl border border-saffron-200 bg-saffron-50 p-3.5">
                <p className="text-xs leading-relaxed text-saffron-900">
                  <strong className="font-semibold">Completion needs proof.</strong> A project
                  cannot be marked complete until an update carries photographic evidence.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
