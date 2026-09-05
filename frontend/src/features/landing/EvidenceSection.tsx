/**
 * "Don't just say it. Show it." — the evidence model.
 *
 * The load-bearing idea is the verification ladder at the bottom. Uploading a
 * photograph does not make a claim true, and the platform never pretends
 * otherwise: evidence moves from *submitted* to *under verification* to
 * *verified* only by a human decision. This section states that plainly rather
 * than letting a camera icon imply proof.
 */

const KINDS = [
  {
    label: 'Photos',
    detail: 'Show the problem as it is, from where it is.',
    icon: <CameraIcon />,
    tone: 'brand',
  },
  {
    label: 'Videos',
    detail: 'Movement, sound and scale that a still cannot carry.',
    icon: <VideoIcon />,
    tone: 'brand',
  },
  {
    label: 'Location',
    detail: 'Coordinates that let reports about one spot find each other.',
    icon: <PinIcon />,
    tone: 'saffron',
  },
  {
    label: 'Documents',
    detail: 'Work orders, inspection reports, invoices, notices.',
    icon: <DocIcon />,
    tone: 'saffron',
  },
  {
    label: 'Timeline',
    detail: 'Every change, dated, attributed and permanent.',
    icon: <ClockIcon />,
    tone: 'leaf',
  },
] as const;

const TONES = {
  brand: 'bg-brand-50 text-brand-700',
  saffron: 'bg-saffron-50 text-saffron-700',
  leaf: 'bg-leaf-50 text-leaf-700',
};

const LADDER = [
  {
    state: 'Evidence submitted',
    detail: 'Anyone signed in can add evidence. It is published as submitted.',
    dot: 'bg-ink-300',
    chip: 'bg-ink-100 text-ink-600',
  },
  {
    state: 'Under verification',
    detail: 'A moderator or department is checking it against the claim.',
    dot: 'bg-saffron-500',
    chip: 'bg-saffron-50 text-saffron-800',
  },
  {
    state: 'Verified evidence',
    detail: 'A person has checked it. Only this state carries a verified mark.',
    dot: 'bg-leaf-600',
    chip: 'bg-leaf-50 text-leaf-800',
  },
];

export function EvidenceSection() {
  return (
    <section aria-labelledby="evidence-heading" className="border-b border-ink-200 bg-white">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-saffron-600">
            Evidence
          </p>
          <h2
            id="evidence-heading"
            className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
          >
            Don&rsquo;t just say it. Show it.
          </h2>
          <p className="mt-3 text-balance leading-relaxed text-ink-500">
            Attach what you actually have to a problem or an update. Evidence is what turns a
            claim into something a department can act on and a neighbour can check.
          </p>
        </div>

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {KINDS.map((kind) => (
            <li
              key={kind.label}
              className="rounded-2xl border border-ink-200 bg-white p-5 transition hover:-translate-y-1 hover:shadow-lg"
            >
              <span
                className={`flex h-11 w-11 items-center justify-center rounded-xl ${TONES[kind.tone]}`}
              >
                {kind.icon}
              </span>
              <h3 className="mt-4 text-base font-bold text-brand-900">{kind.label}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{kind.detail}</p>
            </li>
          ))}
        </ul>

        {/* The verification ladder. */}
        <div className="mt-12 overflow-hidden rounded-2xl border border-ink-200 bg-ink-50">
          <div className="border-b border-ink-200 px-6 py-4">
            <h3 className="text-base font-bold text-brand-900">
              Uploaded is not the same as verified
            </h3>
            <p className="mt-1 text-sm text-ink-500">
              The interface never blurs the difference, and nothing automated moves evidence up
              this ladder.
            </p>
          </div>

          <ol className="grid gap-px bg-ink-200 sm:grid-cols-3">
            {LADDER.map((rung) => (
              <li key={rung.state} className="bg-white p-6">
                <span
                  className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${rung.chip}`}
                >
                  <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${rung.dot}`} />
                  {rung.state}
                </span>
                <p className="mt-3 text-sm leading-relaxed text-ink-600">{rung.detail}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ icons */

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <rect x="2" y="6" width="20" height="14" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 6l1.5-2.5h5L16 6" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function VideoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <rect x="2" y="5" width="14" height="14" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M16 11l6-3.5v9L16 13v-2Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <path
        d="M12 2.5c3.6 0 6.5 2.9 6.5 6.5 0 5-6.5 12.5-6.5 12.5S5.5 14 5.5 9c0-3.6 2.9-6.5 6.5-6.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="9" r="2.4" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <path
        d="M6 2.5h7l5 5V21a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 21V4a1.5 1.5 0 0 1 1-1.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M13 2.5V8h5M9 13h6M9 17h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 7v5.5l3.5 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
