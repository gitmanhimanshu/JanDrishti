import Link from 'next/link';

import { WhatsAppMark } from '@/features/community/WhatsAppInvite';
import { WHATSAPP_INVITE_URL } from '@/lib/community';

/**
 * "Not only about fixing things."
 *
 * JanDrishti is not just a pipeline from complaint to repair. A large part of
 * what it is for is the argument *around* a problem: what should actually be
 * done, what was tried before, what the government ought to change.
 *
 * That conversation depends most on people who have watched an issue for
 * decades — retired officers, long-serving professionals, older residents whose
 * memory of what was tried in the past is the only place that record exists.
 * This section makes that invitation explicit rather than leaving it implied by
 * a form field.
 */

const THREADS = [
  {
    tag: 'Current issue',
    tone: 'saffron',
    question: 'What should the corporation do about waterlogging this monsoon?',
    meta: '34 replies · 6 verified professionals',
  },
  {
    tag: 'Long-standing',
    tone: 'brand',
    question: 'Why has this junction stayed dangerous for fifteen years?',
    meta: '58 replies · 12 residents who remember the earlier plan',
  },
  {
    tag: 'Policy',
    tone: 'leaf',
    question: 'Should drainage inspection be mandatory before every road tender?',
    meta: '21 replies · 4 retired engineers',
  },
] as const;

const TAG_TONES = {
  saffron: 'bg-saffron-50 text-saffron-800 border-saffron-200',
  brand: 'bg-brand-50 text-brand-800 border-brand-200',
  leaf: 'bg-leaf-50 text-leaf-800 border-leaf-200',
};

const VOICES = [
  'Retired government officers',
  'Long-serving professionals',
  'Older residents',
  'Domain experts',
  'Working professionals',
  'Anyone who remembers what was tried before',
];

export function DiscussionSection() {
  return (
    <section aria-labelledby="discussion-heading" className="border-b border-ink-200 bg-white">
      <div className="mx-auto max-w-content px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.05fr] lg:items-start lg:gap-16">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-saffron-600">
              Discussion
            </p>
            <h2
              id="discussion-heading"
              className="mt-3 text-balance text-3xl font-bold tracking-tight text-brand-900 sm:text-4xl"
            >
              Not only about fixing things — about deciding what should be done
            </h2>
            <p className="mt-4 max-w-lg leading-relaxed text-ink-600">
              Plenty of civic problems are not waiting on a repair crew. They are waiting on a
              decision. JanDrishti is also where people argue that out in public: what the
              government should do about an issue now, and why the last three attempts did not
              hold.
            </p>

            <div className="mt-8 rounded-2xl border border-ink-200 bg-ink-50 p-6">
              <h3 className="text-sm font-bold text-brand-900">
                This part needs the people who were there
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">
                Institutional memory mostly lives in people, not in files. Someone who watched a
                scheme fail in 2009 knows something no dataset holds — and that is exactly the
                contribution this section is asking for.
              </p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {VOICES.map((voice) => (
                  <li
                    key={voice}
                    className="rounded-full border border-ink-200 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700"
                  >
                    {voice}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/experience"
                className="inline-flex items-center justify-center rounded-xl bg-brand-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                Join the discussion
              </Link>
              <a
                href={WHATSAPP_INVITE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-leaf-300 bg-white px-6 py-3 text-sm font-semibold text-leaf-800 transition hover:bg-leaf-50 focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:ring-offset-2"
              >
                <WhatsAppMark className="h-4 w-4" />
                Discuss on WhatsApp
              </a>
            </div>
          </div>

          {/* Live-looking threads. Shaped like the real comment API payload. */}
          <div className="space-y-4">
            {THREADS.map((thread) => (
              <article
                key={thread.question}
                className="rounded-2xl border border-ink-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                <span
                  className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${TAG_TONES[thread.tone]}`}
                >
                  {thread.tag}
                </span>
                <h3 className="mt-3 text-base font-semibold leading-snug text-brand-900">
                  {thread.question}
                </h3>
                <p className="mt-2 text-xs text-ink-500">{thread.meta}</p>
              </article>
            ))}

            <p className="rounded-2xl border border-dashed border-ink-300 p-5 text-sm leading-relaxed text-ink-500">
              <strong className="font-semibold text-brand-900">Disagreement is expected.</strong>{' '}
              Support marks agreement, never correctness — a recommendation with fifty supporters
              is still a recommendation, and the platform never presents it as settled fact.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
