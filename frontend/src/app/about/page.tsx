import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'About',
  description:
    'JanDrishti is a public-first civic intelligence platform: public problems, evidence, professional experience and transparent progress in one place.',
  alternates: { canonical: '/about' },
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-ink-900">About JanDrishti</h1>
      <p className="mt-2 text-sm font-medium uppercase tracking-[0.14em] text-brand-600">
        See. Suggest. Solve.
      </p>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-ink-700">
        <p>
          <strong className="font-semibold">Jan</strong> means people.{' '}
          <strong className="font-semibold">Drishti</strong> means vision or perspective. The name
          describes what the platform is for: the collective perspective, experience and judgement
          of citizens and professionals, brought together where it can actually be used.
        </p>

        <p>
          Most civic reporting stops at the complaint. Something is wrong, a form is filed, and
          nothing visible happens. JanDrishti is built around what comes after: the evidence that
          shows the problem is real, the professional judgement about why it keeps happening, the
          record of which department is responsible, and the proof of what was eventually done.
        </p>

        <h2 className="pt-4 text-xl font-semibold text-ink-900">What we hold to</h2>

        <dl className="space-y-5">
          <div>
            <dt className="font-semibold text-ink-900">Public by default</dt>
            <dd className="mt-1 text-ink-600">
              Every problem, contribution and progress update can be read by anyone, with no
              account. An account is only needed to take part. A civic record that requires a login
              to read is not a public record.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink-900">Evidence over assertion</dt>
            <dd className="mt-1 text-ink-600">
              Uploaded evidence is labelled as uploaded. Only what a person has checked is marked
              verified. We would rather show you an unverified photograph honestly than a verified
              one dishonestly.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink-900">Experience over status</dt>
            <dd className="mt-1 text-ink-600">
              A retired overseer who spent thirty years on drainage often knows more about why a
              road keeps failing than anyone else in the conversation. Contribution here is open to
              working professionals, retired officers, armed forces veterans, domain experts and
              experienced citizens alike.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink-900">Support is a signal, not proof</dt>
            <dd className="mt-1 text-ink-600">
              Ten thousand people agreeing does not make a recommendation correct. Contributions are
              ranked on a blend of verification, relevance, evidence and how actionable they are —
              popularity is one input among several, and a small one.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink-900">People decide the things that matter</dt>
            <dd className="mt-1 text-ink-600">
              Automated tools categorise, route and flag probable duplicates. They never decide
              whether an allegation is true, whether evidence is genuine, whether an official has
              done wrong, or whether a professional claim is verified.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink-900">Privacy is designed in</dt>
            <dd className="mt-1 text-ink-600">
              Verification documents are stored privately, access to them is logged, and they are
              deleted on a schedule. Aadhaar is never required, never a login, never stored as a
              number, and never shown publicly.
            </dd>
          </div>
        </dl>

        <h2 className="pt-4 text-xl font-semibold text-ink-900">What this is not</h2>
        <p>
          JanDrishti is not a court and not an investigator. A report here is an account of what
          somebody saw, alongside whatever evidence they could gather. Serious allegations are
          handled as claims requiring review, not as findings — and the interface says so rather
          than leaving you to guess.
        </p>
      </div>
    </div>
  );
}
